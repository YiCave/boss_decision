import { useState } from "react";
import { FileText, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { DocumentUpload } from "@/components/documents/DocumentUpload";
import { DocumentList } from "@/components/documents/DocumentList";

const DocumentsPage = () => {
  const navigate = useNavigate();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = () => {
    // Trigger refresh of document list
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50/40 via-orange-50/30 to-emerald-50/20">
      {/* Header */}
      <header className="border-b border-gray-200/30 bg-white/60 backdrop-blur-md sticky top-0 z-10 shadow-sm shadow-gray-900/5">
        {/* Same width + horizontal padding as <main> so title aligns with the Upload card */}
        <div className="w-full max-w-[95%] mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/")}
              className="text-gray-600 hover:text-gray-800 hover:bg-gray-100/50 rounded-full transition-all duration-200"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-orange-400/90 to-orange-500/90 flex items-center justify-center shadow-lg shadow-orange-500/20">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-800 leading-tight tracking-tight">
                Document Management
              </h1>
              <p className="text-xs text-gray-500 font-light">
                Upload and manage business documents with AI extraction
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full max-w-[95%] mx-auto px-4 sm:px-6 py-8">
        {/* Side-by-side layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:items-start">
          {/* Upload Section - Left: only as tall as its content (do not stretch to match right column) */}
          <div className="lg:col-span-4">
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          </div>

          {/* Documents List Section - Right side (bigger) */}
          <div className="lg:col-span-8">
            <DocumentList refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </main>
    </div>
  );
};

export default DocumentsPage;
