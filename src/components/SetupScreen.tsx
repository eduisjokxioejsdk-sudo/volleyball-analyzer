import { useState, useRef } from "react";
import { ArrowLeft, Upload, Loader2, FileVideo, Settings2, CheckCircle2, Sparkles, AlertCircle, Brain } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { uploadToWasabi, isWasabiConfigured, getWasabiUrl } from "@/lib/wasabiStorage";
import type { TeamSide, TeamNames, DetectedPoint } from "@/pages/Index";

const TEST_MODE = false;
const TEST_USER_ID = "00000000-0000-0000-0000-000000000000";

const VOLLEYVISION_API = import.meta.env.VITE_VOLLEYVISION_API_URL || "http://localhost:5000";

export interface SetupResult {
  servingTeam: TeamSide;
  rotation: number;
  names: TeamNames;
  videoTitle: string;
  storagePath: string | null;
  videoFile: File | null;
  detectedPoints: DetectedPoint[];
  videoId?: string;
}

interface SetupScreenProps {
  onComplete: (data: SetupResult) => void;
  onBack: () => void;
}

const rotations = [1, 2, 3, 4, 5, 6];

const SetupScreen = ({ onComplete, onBack }: SetupScreenProps) => {
  const { user: authUser } = useAuth();
  const { toast } = useToast();
  const user = TEST_MODE ? { id: TEST_USER_ID } as unknown as { id: string } : authUser;
  const [videoTitle, setVideoTitle] = useState("");
  const [teamA, setTeamA] = useState("Mon Équipe");
  const [teamB, setTeamB] = useState("Adversaire");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [storagePath, setStoragePath] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [servingTeam, setServingTeam] = useState<TeamSide>("A");
  const [rotation, setRotation] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;
    setVideoFile(file);
    setUploadProgress(0);
    setUploadComplete(false);
    setUploadError(null);
    setStoragePath(null);
    if (!videoTitle) setVideoTitle(file.name.replace(/\.[^/.]+$/, ""));
    setUploading(true);

    try {
      if (isWasabiConfigured()) {
        const result = await uploadToWasabi(file, user.id, (progress) => {
          setUploadProgress(progress);
        });
        if (!result.success || !result.key) {
          throw new Error(result.error || "Upload échoué");
        }
        setStoragePath(result.url || result.key);
        setUploadProgress(100);
        setUploadComplete(true);
        toast({ title: "Upload terminé !" });
      } else {
        setUploadProgress(10);
        const ext = file.name.split(".").pop() || "mp4";
        const path = `${user.id}/${Date.now()}.${ext}`;
        const { error } = await supabase.storage
          .from("match-videos")
          .upload(path, file, { contentType: file.type || "video/mp4", upsert: false });
        if (error) throw new Error(error.message);
        setStoragePath(path);
        setUploadProgress(100);
        setUploadComplete(true);
        toast({ title: "Upload terminé !" });
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadError(err.message || "Erreur lors de l'upload");
      toast({ title: "Erreur d'upload", description: err.message, variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  const canFinish = videoTitle.trim().length > 0 && uploadComplete && storagePath && !submitting;

  const handleFinish = async () => {
    if (!videoFile || !user || !storagePath) return;
    setSubmitting(true);

    try {
      // 1. Créer l'enregistrement vidéo en DB avec status PROCESSING
      const { data: insertedVideo, error: dbError } = await supabase.from("videos").insert({
        title: videoTitle.trim(),
        user_id: user.id,
        status: "PROCESSING",
        progress: 0,
        video_url: storagePath,
        team_a_name: teamA,
        team_b_name: teamB,
        serving_team: servingTeam,
        initial_rotation: rotation,
        points_data: [],
      } as any).select().single();

      if (dbError) {
        console.error("DB insert error:", dbError);
        toast({ title: "Erreur DB", description: `${dbError.message} (${dbError.code})`, variant: "destructive" });
        setSubmitting(false);
        return;
      }

      const videoId = (insertedVideo as any)?.id;

      // 2. Obtenir l'URL publique de la vidéo
      let videoUrl = storagePath;
      if (!videoUrl.startsWith("http") && isWasabiConfigured()) {
        videoUrl = await getWasabiUrl(storagePath);
      }

      // 3. L'analyse est gérée par le worker GPU Vast.ai
      // Le worker surveille la table 'videos' pour status='PROCESSING'
      // et lance automatiquement l'analyse avec GPU
      console.log(`✅ Vidéo ${videoId} créée avec status=PROCESSING → le worker GPU va la traiter`);

      toast({
        title: "🏐 Vidéo créée !",
        description: "L'analyse YOLO Volleyball est en cours. Vous pouvez fermer le navigateur.",
      });

      // 4. Retour immédiat au dashboard
      onComplete({
        servingTeam,
        rotation,
        names: { teamA, teamB },
        videoTitle,
        storagePath,
        videoFile: null, // Don't keep file in memory
        detectedPoints: [],
        videoId,
      });
    } catch (err: any) {
      toast({ title: "Erreur", description: err.message, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background relative">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="bg-orb bg-orb-purple w-[500px] h-[500px] -top-40 left-1/3 animate-float-slow" />
        <div className="bg-orb bg-orb-pink w-[300px] h-[300px] bottom-0 right-0 animate-float-delayed" />
      </div>

      {/* Header */}
      <header className="animate-slide-down sticky top-0 z-40">
        <div className="mx-3 mt-3">
          <div className="liquid-glass-strong rounded-2xl px-6 py-3 flex items-center gap-3">
            <button onClick={onBack} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground text-sm transition-colors">
              <ArrowLeft className="w-4 h-4" />Retour
            </button>
            <div className="flex-1 flex items-center justify-center gap-2">
              <Sparkles className="w-4 h-4 text-cv-cta" />
              <h1 className="text-lg font-display font-bold from-yellow-300 to-yellow-100 bg-clip-text text-transparent">
                Nouvelle analyse
              </h1>
            </div>
            <div className="w-16" />
          </div>
        </div>
      </header>

      <div className="relative z-10 container mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-3 gap-5 max-w-6xl mx-auto stagger-children">
          {/* Upload */}
          <div className="liquid-glass-strong rounded-2xl p-6 space-y-5">
            <div className="text-center">
              <div className="mx-auto w-14 h-14 rounded-2xl bg-cv-cta flex items-center justify-center mb-3 glow-purple-sm">
                <FileVideo className="w-7 h-7 text-cv-cta-ink" />
              </div>
              <h2 className="font-display font-bold text-lg">Importer</h2>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Nom de la vidéo</label>
              <input value={videoTitle} onChange={e => setVideoTitle(e.target.value)} placeholder="Ex: Match vs Paris" className="w-full px-3 py-2.5 rounded-xl bg-muted/30 border border-border/50 text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:border-cv-cta/40 focus:ring-2 focus:ring-cv-cta/15 transition-all" />
            </div>
            <div>
              <input ref={fileInputRef} type="file" accept="video/*" onChange={handleFileSelect} className="hidden" />
              {!videoFile ? (
                <button onClick={() => fileInputRef.current?.click()} className="w-full border-2 border-dashed border-cv-cta/20 rounded-xl p-8 flex flex-col items-center gap-3 hover:border-cv-cta/40 hover:bg-cv-cta/5 transition-all group cursor-pointer">
                  <Upload className="w-10 h-10 text-muted-foreground group-hover:text-cv-cta transition-colors" />
                  <span className="text-sm text-muted-foreground group-hover:text-cv-cta">Sélectionner un fichier vidéo</span>
                  <span className="text-[10px] text-muted-foreground/50">MP4, MOV, AVI</span>
                </button>
              ) : (
                <div className="rounded-xl bg-muted/20 border border-border/30 p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <FileVideo className="w-6 h-6 text-cv-cta shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{videoFile.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {videoFile.size > 1024 * 1024 * 1024
                          ? `${(videoFile.size / (1024 * 1024 * 1024)).toFixed(2)} GB`
                          : `${(videoFile.size / (1024 * 1024)).toFixed(1)} MB`}
                      </p>
                    </div>
                    {!uploading && !uploadComplete && (
                      <button onClick={() => { setVideoFile(null); setUploadError(null); }} className="text-xs text-muted-foreground hover:text-foreground">✕</button>
                    )}
                  </div>
                  {uploading && (
                    <div className="space-y-1.5">
                      <Progress value={uploadProgress} className="h-2" />
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground flex items-center gap-1.5">
                          <Loader2 className="w-3 h-3 animate-spin text-cv-cta" />
                          Upload en cours...
                        </span>
                        <span className="text-cv-cta font-medium">{uploadProgress}%</span>
                      </div>
                    </div>
                  )}
                  {uploadComplete && (
                    <div className="flex items-center gap-2 text-emerald-400 text-xs bg-emerald-400/10 rounded-lg p-2.5">
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="font-medium">Upload terminé avec succès !</span>
                    </div>
                  )}
                  {uploadError && (
                    <div className="flex items-center gap-2 text-destructive text-xs bg-destructive/10 rounded-lg p-2.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>{uploadError}</span>
                      <button onClick={() => fileInputRef.current?.click()} className="ml-auto text-cv-cta hover:text-cv-cta underline">Réessayer</button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Config */}
          <div className="liquid-glass-strong rounded-2xl p-6 space-y-5">
            <div className="text-center">
              <div className="mx-auto w-14 h-14 rounded-2xl bg-cv-cta flex items-center justify-center mb-3 glow-purple-sm">
                <Settings2 className="w-7 h-7 text-cv-cta-ink" />
              </div>
              <h2 className="font-display font-bold text-lg">Configuration</h2>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Équipes</label>
              <div className="grid grid-cols-2 gap-2">
                <input value={teamA} onChange={e => setTeamA(e.target.value)} placeholder="Équipe A" className="px-3 py-2.5 rounded-xl bg-muted/30 border border-border/50 text-sm text-foreground focus:outline-none focus:border-cv-cta/40 transition-all" />
                <input value={teamB} onChange={e => setTeamB(e.target.value)} placeholder="Équipe B" className="px-3 py-2.5 rounded-xl bg-muted/30 border border-border/50 text-sm text-foreground focus:outline-none focus:border-cv-cta/40 transition-all" />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Premier service</label>
              <div className="flex gap-2">
                {(["A", "B"] as TeamSide[]).map(side => (
                  <button key={side} onClick={() => setServingTeam(side)}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${servingTeam === side ? "bg-cv-cta text-cv-cta-ink glow-purple-sm" : "bg-muted/30 border border-border/50 text-muted-foreground hover:border-cv-cta/30"}`}>
                    {side === "A" ? teamA : teamB}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Position passeur</label>
              <div className="grid grid-cols-6 gap-1.5">
                {rotations.map(r => (
                  <button key={r} onClick={() => setRotation(r)}
                    className={`h-9 rounded-lg text-xs font-bold transition-all ${rotation === r ? "bg-cv-cta text-cv-cta-ink glow-purple-sm" : "bg-muted/30 border border-border/50 text-muted-foreground hover:border-cv-cta/30"}`}>
                    P{r}
                  </button>
                ))}
              </div>
            </div>

            <button
              className="liquid-btn w-full py-3 rounded-xl bg-cv-cta text-cv-cta-ink font-semibold glow-purple-sm disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              disabled={!canFinish || uploading}
              onClick={handleFinish}
            >
              {submitting ? (
                <><Loader2 className="w-4 h-4 animate-spin" />Création en cours…</>
              ) : uploading ? (
                <><Loader2 className="w-4 h-4 animate-spin" />Upload en cours…</>
              ) : uploadComplete ? (
                <><Brain className="w-4 h-4" />Lancer l'analyse</>
              ) : (
                "Sélectionne une vidéo d'abord"
              )}
            </button>
          </div>

          {/* Info */}
          <div className="space-y-4">
            <div className="liquid-glass-card rounded-2xl p-5 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-cv-cta flex items-center justify-center shrink-0 glow-purple-sm">
                <Brain className="w-6 h-6 text-cv-cta-ink" />
              </div>
              <div>
                <h3 className="font-display font-bold">YOLO Volleyball</h3>
                <p className="text-xs text-muted-foreground">Analyse IA par détection vidéo</p>
              </div>
            </div>
            {[
              "Détection automatique des points",
              "Attribution du score par IA",
              "Suivi des rotations P1→P6",
            ].map((text, i) => (
              <div key={i} className="liquid-glass-card rounded-xl p-3 flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-cv-cta shrink-0" />
                <span className="text-sm text-muted-foreground">{text}</span>
              </div>
            ))}

            {/* Analyse system info */}
            <div className="liquid-glass-strong rounded-2xl p-5 space-y-3">
              <h3 className="font-display font-bold text-sm">🏐 Comment ça marche ?</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Notre IA YOLO Volleyball analyse chaque frame de ta vidéo pour détecter la balle, 
                les joueurs et les actions de jeu. Les points sont découpés automatiquement 
                et le score est calculé en temps réel.
              </p>
              <p className="text-xs text-cv-cta leading-relaxed font-medium">
                💡 Tu peux fermer ton navigateur pendant l'analyse, 
                les résultats apparaîtront automatiquement sur ton tableau de bord.
              </p>
              <div className="grid grid-cols-3 gap-3 text-center pt-2">
                <div>
                  <p className="text-lg font-display font-bold text-cv-cta">YOLOv8</p>
                  <p className="text-[10px] text-muted-foreground">Modèle IA</p>
                </div>
                <div>
                  <p className="text-lg font-display font-bold text-pink-300">Auto</p>
                  <p className="text-[10px] text-muted-foreground">Score</p>
                </div>
                <div>
                  <p className="text-lg font-display font-bold text-cv-cta">Cloud</p>
                  <p className="text-[10px] text-muted-foreground">Analyse</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SetupScreen;
