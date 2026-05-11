import { useState, useCallback } from "react";
import { Upload, File, Check, X, Loader2, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DocumentUploadProps {
  onUploadSuccess?: () => void;
}

export const DocumentUpload = ({ onUploadSuccess }: DocumentUploadProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "success" | "error">("idle");
  const [currentStage, setCurrentStage] = useState<string>("Uploading...");
  const [customExtraction, setCustomExtraction] = useState("");
  const { toast } = useToast();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const uploadFile = async (file: File) => {
    setUploading(true);
    setProgress(0);
    setUploadStatus("idle");
    setCurrentStage("Uploading to cloud storage...");

    // Realistic multi-stage progress simulation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev < 20) {
          setCurrentStage("Uploading to cloud storage...");
          return prev + 2;
        } else if (prev < 40) {
          setCurrentStage("Analyzing document with AI...");
          return prev + 1;
        } else if (prev < 70) {
          setCurrentStage("Extracting data (this may take 30-60 seconds)...");
          return prev + 0.5;
        } else if (prev < 90) {
          setCurrentStage("Writing to database...");
          return prev + 0.3;
        }
        return Math.min(prev + 0.1, 95);
      });
    }, 500);  // Update every 500ms

    try {
      const formData = new FormData();
      formData.append("file", file);
      
      // Add custom extraction if provided
      if (customExtraction.trim()) {
        formData.append("custom_extraction", customExtraction.trim());
      }

      // 90-second timeout for AI processing
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);

      const response = await fetch("http://localhost:8000/api/documents/upload", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      clearInterval(progressInterval);
      setProgress(100);
      setCurrentStage("Complete!");

      const result = await response.json();

      if (response.ok && result.success) {
        setUploadStatus("success");
        toast({
          title: "Upload successful!",
          description: `${file.name} has been processed and data extracted.`,
        });
        onUploadSuccess?.();
        
        // Reset after 3 seconds
        setTimeout(() => {
          setUploading(false);
          setProgress(0);
          setUploadStatus("idle");
          setCurrentStage("Uploading...");
          setCustomExtraction(""); // Clear custom extraction field
        }, 3000);
      } else {
        clearInterval(progressInterval);
        throw new Error(result.error || "Upload failed");
      }
    } catch (error) {
      clearInterval(progressInterval);
      setUploadStatus("error");
      
      // Handle timeout specifically
      if (error instanceof Error && error.name === 'AbortError') {
        toast({
          title: "Processing timeout",
          description: "Document processing took longer than expected. Please try again or upload a smaller file.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Upload failed",
          description: error instanceof Error ? error.message : "An error occurred during upload",
          variant: "destructive",
        });
      }
      
      setCurrentStage("Failed");
      setTimeout(() => {
        setUploading(false);
        setProgress(0);
        setUploadStatus("idle");
        setCurrentStage("Uploading...");
      }, 3000);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  }, []);

  return (
    <Card className="border border-gray-200/40 bg-white/70 backdrop-blur-sm shadow-lg shadow-gray-900/5 rounded-2xl transition-all duration-300 hover:shadow-xl hover:shadow-gray-900/10">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-orange-400/90 to-orange-500/90 flex items-center justify-center shadow-md shadow-orange-500/20">
            <Upload className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-800 tracking-tight">Upload</h2>
            <p className="text-xs text-gray-500 font-light">
              AI extraction
            </p>
          </div>
        </div>

        {/* Custom Extraction Field */}
        <div className="space-y-2 mb-5">
          <Label htmlFor="custom-extraction" className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Sparkles className="w-4 h-4 text-orange-500" />
            What specific data do you want to extract? (Optional)
          </Label>
          <Input
            id="custom-extraction"
            type="text"
            placeholder="e.g., team morale score, customer satisfaction rating..."
            value={customExtraction}
            onChange={(e) => setCustomExtraction(e.target.value)}
            disabled={uploading}
            className="border-gray-200/50 bg-white/80 focus:border-orange-300 focus:ring-orange-300/30 rounded-xl transition-all duration-200"
          />
          <p className="text-xs text-gray-500 font-light">
            Custom data will be saved in the AI justification field for reference.
          </p>
        </div>

        {/* Drag and Drop Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            relative border border-dashed rounded-2xl p-8 text-center transition-all duration-300
            ${isDragging ? "border-orange-400 bg-orange-50/50 scale-[1.02]" : "border-gray-300/60 bg-gradient-to-br from-gray-50/50 to-white/50"}
            ${uploading ? "pointer-events-none" : "cursor-pointer hover:border-orange-300 hover:bg-orange-50/30 hover:shadow-inner"}
          `}
        >
          <input
            type="file"
            id="file-upload"
            className="hidden"
            onChange={handleFileSelect}
            accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg,.xlsx,.csv"
            disabled={uploading}
          />

          {!uploading && uploadStatus === "idle" && (
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-orange-100/80 to-orange-200/60 flex items-center justify-center mb-3 shadow-sm">
                <File className="w-7 h-7 text-orange-600" />
              </div>
              <p className="text-base font-medium text-gray-700 mb-1">
                Drop files here
              </p>
              <p className="text-xs text-gray-500 font-light">
                or click to browse
              </p>
              <p className="text-xs text-gray-400 mt-2 font-light">
                PDF, Word, Excel, Images
              </p>
            </label>
          )}

          {uploading && uploadStatus === "idle" && (
            <div className="space-y-4">
              <Loader2 className="w-12 h-12 mx-auto text-orange-500 animate-spin" />
              <p className="text-base font-medium text-gray-700">{currentStage}</p>
              <p className="text-sm text-gray-500 font-light">
                {progress < 20 ? "Uploading file to cloud..." :
                 progress < 40 ? "AI is reading your document..." :
                 progress < 70 ? "This may take 30-60 seconds for AI processing" :
                 progress < 90 ? "Saving extracted data..." :
                 "Finalizing..."}
              </p>
              <div className="max-w-md mx-auto">
                <Progress value={progress} className="h-1.5 bg-gray-200/50" />
                <p className="text-xs text-gray-400 mt-2 text-center font-light">
                  {Math.round(progress)}% complete
                </p>
              </div>
            </div>
          )}

          {uploadStatus === "success" && (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-green-100/80 to-emerald-100/60 flex items-center justify-center shadow-sm">
                <Check className="w-8 h-8 text-green-600" />
              </div>
              <p className="text-base font-medium text-gray-700">Upload successful!</p>
              <p className="text-sm text-gray-500 font-light">Document processed and data extracted</p>
            </div>
          )}

          {uploadStatus === "error" && (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-red-100/80 to-rose-100/60 flex items-center justify-center shadow-sm">
                <X className="w-8 h-8 text-red-600" />
              </div>
              <p className="text-base font-medium text-gray-700">Upload failed</p>
              <p className="text-sm text-gray-500 font-light">Please try again</p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
