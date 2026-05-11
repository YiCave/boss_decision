import { useState } from "react";
import { FileText, ExternalLink, Trash2, Calendar, File } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";

interface Document {
  source_id: number;
  doc_type: string;
  title: string;
  file_path: string;
  published_date: string | null;
  extracted_at: string | null;
  created_at: string;
}

interface DocumentCardProps {
  document: Document;
  onDelete?: () => void;
}

export const DocumentCard = ({ document, onDelete }: DocumentCardProps) => {
  const { toast } = useToast();
  const [imageError, setImageError] = useState(false);

  const handleDelete = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/documents/${document.source_id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        toast({
          title: "Document deleted",
          description: "The document has been successfully deleted.",
        });
        onDelete?.();
      } else {
        throw new Error("Failed to delete document");
      }
    } catch (error) {
      toast({
        title: "Delete failed",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  };

  const getDocTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      "HR Report": "bg-blue-100 text-blue-700 border-blue-300",
      "Sales Log": "bg-green-100 text-green-700 border-green-300",
      "Finance Report": "bg-purple-100 text-purple-700 border-purple-300",
      "Marketing Report": "bg-pink-100 text-pink-700 border-pink-300",
      "Supply Chain Log": "bg-yellow-100 text-yellow-700 border-yellow-300",
      "Legal Policy": "bg-gray-100 text-gray-700 border-gray-300",
      "Employee": "bg-indigo-100 text-indigo-700 border-indigo-300",
    };
    return colors[type] || "bg-orange-100 text-orange-700 border-orange-300";
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A";
    try {
      return format(new Date(dateString), "MMM dd, yyyy");
    } catch {
      return "N/A";
    }
  };

  // Generate Cloudinary preview URL for any file type
  const getCloudinaryPreview = (url: string): string | null => {
    if (!url.includes('cloudinary.com')) return null;
    
    // Extract file extension
    const ext = url.split('.').pop()?.toLowerCase();
    
    // For images, return as-is (Cloudinary serves them directly)
    const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'];
    if (imageExts.includes(ext || '')) {
      // Add transformation for consistent preview size
      return url.replace('/upload/', '/upload/w_800,h_600,c_fit/');
    }
    
    // For PDFs, generate image preview of first page
    if (ext === 'pdf') {
      return url.replace('/upload/', '/upload/w_800,h_600,c_fit,pg_1,f_jpg/').replace('.pdf', '.jpg');
    }
    
    // For documents (doc, docx, etc.), Cloudinary can generate previews
    const docExts = ['doc', 'docx', 'ppt', 'pptx'];
    if (docExts.includes(ext || '')) {
      return url.replace('/upload/', '/upload/w_800,h_600,c_fit,pg_1,f_jpg/').replace(`.${ext}`, '.jpg');
    }
    
    return null;
  };

  // Check file types for fallback icons
  const getFileType = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase() || '';
    
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(ext)) return 'image';
    if (ext === 'pdf') return 'pdf';
    if (['doc', 'docx', 'txt', 'md', 'rtf'].includes(ext)) return 'document';
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'spreadsheet';
    
    return 'unknown';
  };

  const previewUrl = getCloudinaryPreview(document.file_path);
  const fileType = getFileType(document.file_path);

  return (
    <Card className="border border-gray-200/40 hover:border-orange-200/60 hover:shadow-lg hover:shadow-gray-900/10 transition-all duration-300 bg-white/80 backdrop-blur-sm overflow-hidden rounded-2xl hover:scale-[1.02]">
      {/* Cloudinary Preview (works for images, PDFs, and documents) */}
      {previewUrl && !imageError ? (
        <div 
          className="w-full h-48 bg-gradient-to-br from-gray-100/50 to-gray-50/30 overflow-hidden cursor-pointer group"
          onClick={() => window.open(document.file_path, "_blank")}
        >
          <img 
            src={previewUrl} 
            alt={document.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
            onError={() => setImageError(true)}
          />
        </div>
      ) : (
        // Fallback for non-Cloudinary files or unsupported types
        <div 
          className="w-full h-48 bg-gradient-to-br from-gray-50/70 to-white/50 overflow-hidden cursor-pointer hover:from-orange-50/30 hover:to-amber-50/20 transition-all duration-300 flex items-center justify-center"
          onClick={() => window.open(document.file_path, "_blank")}
        >
          <div className="text-center">
            {fileType === 'pdf' && (
              <>
                <FileText className="w-14 h-14 text-red-500/80 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">PDF Document</p>
              </>
            )}
            {fileType === 'document' && (
              <>
                <File className="w-14 h-14 text-blue-500/80 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">Document</p>
              </>
            )}
            {fileType === 'spreadsheet' && (
              <>
                <FileText className="w-14 h-14 text-green-500/80 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">Spreadsheet</p>
              </>
            )}
            {fileType === 'unknown' && (
              <>
                <File className="w-14 h-14 text-gray-500/80 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">File</p>
              </>
            )}
            <p className="text-xs text-gray-400 mt-1 font-light">Click to view</p>
          </div>
        </div>
      )}
      
      <div className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-100/80 to-orange-200/60 flex items-center justify-center flex-shrink-0 shadow-sm">
            <FileText className="w-5 h-5 text-orange-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-gray-700 truncate text-sm" title={document.title}>
              {document.title}
            </h3>
            <Badge className={`mt-1.5 text-xs border ${getDocTypeColor(document.doc_type)}`}>
              {document.doc_type}
            </Badge>
          </div>
        </div>

        {/* Metadata */}
        <div className="space-y-1.5 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs font-light">Uploaded: {formatDate(document.created_at)}</span>
          </div>
          {document.extracted_at && (
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
              <span className="text-xs font-light text-emerald-600">Processed & extracted</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 text-orange-600 border-orange-200/60 hover:bg-gradient-to-br hover:from-orange-50/50 hover:to-amber-50/30 hover:text-orange-700 rounded-xl transition-all duration-200 hover:border-orange-300/80 shadow-sm"
            onClick={() => window.open(document.file_path, "_blank")}
          >
            <ExternalLink className="w-3.5 h-3.5 mr-2" />
            View
          </Button>
          
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="text-red-500 border-red-200/60 hover:bg-gradient-to-br hover:from-red-50/50 hover:to-rose-50/30 hover:text-red-600 rounded-xl transition-all duration-200 hover:border-red-300/80 shadow-sm"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="rounded-2xl border-gray-200/40 shadow-2xl">
              <AlertDialogHeader>
                <AlertDialogTitle className="text-gray-800">Delete document?</AlertDialogTitle>
                <AlertDialogDescription className="text-gray-500 font-light">
                  This will permanently delete "{document.title}" and all related data.
                  This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="rounded-xl border-gray-200/60 hover:bg-gray-50 transition-all duration-200">Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className="bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-xl shadow-md shadow-red-500/20 transition-all duration-200"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </Card>
  );
};
