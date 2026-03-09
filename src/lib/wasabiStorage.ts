/**
 * Wasabi S3 Storage Service
 * Génère des URLs présignées pour sécuriser l'accès aux vidéos
 */

import { S3Client, GetObjectCommand, DeleteObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { Upload } from "@aws-sdk/lib-storage";

const wasabiConfig = {
  region: (import.meta.env.VITE_WASABI_REGION || "eu-west-2").trim(),
  credentials: {
    accessKeyId: (import.meta.env.VITE_WASABI_ACCESS_KEY || "").trim(),
    secretAccessKey: (import.meta.env.VITE_WASABI_SECRET_KEY || "").trim(),
  },
  endpoint: (import.meta.env.VITE_WASABI_ENDPOINT || "https://s3.eu-west-2.wasabisys.com").trim(),
  forcePathStyle: true,
};

const bucketName = (import.meta.env.VITE_WASABI_BUCKET || "courtvision").trim();

const s3Client = new S3Client(wasabiConfig);

export interface UploadResult {
  success: boolean;
  key?: string;
  url?: string;
  error?: string;
}

/**
 * Upload un fichier vers Wasabi
 */
export async function uploadToWasabi(
  file: File,
  userId: string,
  onProgress?: (progress: number) => void
): Promise<UploadResult> {
  try {
    const key = `${userId}/${Date.now()}-${file.name.replace(/\s+/g, "-")}`;

    // Upload multipart en streaming - pas de chargement en mémoire
    const upload = new Upload({
      client: s3Client,
      params: {
        Bucket: bucketName,
        Key: key,
        Body: file, // Stream direct du File (Blob) - PAS de arrayBuffer()
        ContentType: file.type || "video/mp4",
      },
      // Optimisations multipart pour gros fichiers vidéo
      queueSize: 4,              // 4 parts en parallèle
      partSize: 10 * 1024 * 1024, // Parts de 10MB (au lieu de 5MB par défaut)
      leavePartsOnError: false,    // Nettoyer en cas d'erreur
    });

    upload.on("httpUploadProgress", (progress) => {
      if (progress.loaded && progress.total) {
        const pct = Math.round((progress.loaded / progress.total) * 100);
        onProgress?.(pct);
      }
    });

    await upload.done();

    // Generate presigned URL for 24 hours
    const url = await generatePresignedUrl(key);

    return {
      success: true,
      key,
      url,
    };
  } catch (error) {
    console.error("Wasabi upload error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Upload failed",
    };
  }
}

/**
 * Supprime un fichier de Wasabi
 */
export async function deleteFromWasabi(key: string): Promise<boolean> {
  try {
    // If it's a full URL, extract the key
    let actualKey = key;
    if (key.startsWith('http')) {
      // Extract key from URL like https://s3.eu-west-2.wasabisys.com/bucket/key
      const urlParts = key.split(`/${bucketName}/`);
      if (urlParts.length > 1) {
        actualKey = urlParts[1];
      } else {
        // Try to use the key as-is
        actualKey = key;
      }
    }

    const command = new DeleteObjectCommand({
      Bucket: bucketName,
      Key: actualKey,
    });

    await s3Client.send(command);
    return true;
  } catch (error) {
    console.error("Wasabi delete error:", error);
    return false;
  }
}

/**
 * Génère une URL présignée pour accéder à un fichier
 */
export async function generatePresignedUrl(key: string, expiresInSeconds = 86400): Promise<string> {
  try {
    const command = new GetObjectCommand({
      Bucket: bucketName,
      Key: key,
    });
    
    const signedUrl = await getSignedUrl(s3Client, command, { expiresIn: expiresInSeconds });
    return signedUrl;
  } catch (error) {
    console.error("Error generating presigned URL:", error);
    throw error;
  }
}

/**
 * Get URL - generates presigned URL if needed
 */
export async function getWasabiUrl(key: string): Promise<string> {
  // If it's already a presigned URL or full URL, return it
  if (key.startsWith('http')) {
    return key;
  }
  // Generate new presigned URL
  return generatePresignedUrl(key);
}

/**
 * Check if Wasabi is configured
 */
export function isWasabiConfigured(): boolean {
  return !!(
    import.meta.env.VITE_WASABI_ACCESS_KEY &&
    import.meta.env.VITE_WASABI_SECRET_KEY &&
    import.meta.env.VITE_WASABI_BUCKET
  );
}
