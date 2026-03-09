-- Migration: Créer la table matches pour PureVolley Worker
-- Cette table est utilisée par le worker IA pour traiter les vidéos de volley

CREATE TABLE IF NOT EXISTS public.matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  video_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  title TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index pour accélérer les requêtes du worker
CREATE INDEX IF NOT EXISTS idx_matches_status ON public.matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_user_id ON public.matches(user_id);
CREATE INDEX IF NOT EXISTS idx_matches_created_at ON public.matches(created_at);

-- RLS : Activer la sécurité au niveau des lignes
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;

-- Politique : Les utilisateurs peuvent voir leurs propres matchs
CREATE POLICY "Users can view own matches"
  ON public.matches
  FOR SELECT
  USING (auth.uid() = user_id);

-- Politique : Les utilisateurs peuvent créer des matchs
CREATE POLICY "Users can create matches"
  ON public.matches
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Politique : Le service_role peut tout faire (pour le worker)
CREATE POLICY "Service role full access"
  ON public.matches
  FOR ALL
  USING (auth.role() = 'service_role');

-- Trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_matches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_matches_updated_at
  BEFORE UPDATE ON public.matches
  FOR EACH ROW
  EXECUTE FUNCTION update_matches_updated_at();

-- Commentaire sur la table
COMMENT ON TABLE public.matches IS 'Table des matchs de volley pour le traitement IA par PureVolley Worker';
COMMENT ON COLUMN public.matches.status IS 'Status du match: pending, processing, completed, failed';
COMMENT ON COLUMN public.matches.video_url IS 'URL S3 de la vidéo sur Wasabi';
COMMENT ON COLUMN public.matches.metadata IS 'Résultats du traitement IA en JSON';
