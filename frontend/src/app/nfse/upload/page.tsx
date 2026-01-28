"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useNfseStore } from "@/lib/store";
import { extractNfseFile } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  Briefcase,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { translateDocumentClass, getServiceClassColor } from "@/types/nfse";

interface FileStatus {
  file: File;
  status: "pending" | "processing" | "success" | "error";
  error?: string;
  result?: any;
  notesCount?: number;
}

export default function NfseUploadPage() {
  const router = useRouter();
  const { addNfse, clearNfseNotes, nfseNotes } = useNfseStore();
  const [files, setFiles] = useState<FileStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleClearAllNotes = () => {
    if (confirm("Tem certeza que deseja limpar todas as NFS-e processadas?")) {
      clearNfseNotes();
      setFiles([]);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const isValidFile = (f: File) => {
    const name = f.name.toLowerCase();
    return name.endsWith(".xml") || name.endsWith(".zip");
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(isValidFile);

    if (droppedFiles.length > 0) {
      setFiles((prev) => [
        ...prev,
        ...droppedFiles.map((file) => ({ file, status: "pending" as const })),
      ]);
    }
  }, []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(e.target.files || []).filter(isValidFile);

      if (selectedFiles.length > 0) {
        setFiles((prev) => [
          ...prev,
          ...selectedFiles.map((file) => ({ file, status: "pending" as const })),
        ]);
      }
    },
    []
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearAll = useCallback(() => {
    setFiles([]);
  }, []);

  const processFiles = async () => {
    setIsProcessing(true);

    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== "pending") continue;

      setFiles((prev) =>
        prev.map((f, idx) =>
          idx === i ? { ...f, status: "processing" as const } : f
        )
      );

      try {
        const results = await extractNfseFile(files[i].file);
        
        let firstResult = null;
        for (const result of results) {
          addNfse(result.filename || files[i].file.name, result);
          if (!firstResult) firstResult = result;
        }

        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { 
              ...f, 
              status: "success" as const, 
              result: firstResult,
              notesCount: results.length
            } : f
          )
        );
      } catch (error) {
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i
              ? {
                  ...f,
                  status: "error" as const,
                  error: error instanceof Error ? error.message : "Erro desconhecido",
                }
              : f
          )
        );
      }
    }

    setIsProcessing(false);
  };

  const successCount = files.filter((f) => f.status === "success").length;
  const pendingCount = files.filter((f) => f.status === "pending").length;

  const getReviewLevelColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "LOW":
        return "bg-green-100 text-green-800";
      case "MEDIUM":
        return "bg-yellow-100 text-yellow-800";
      case "HIGH":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  const translateReviewLevel = (level: string) => {
    switch (level?.toUpperCase()) {
      case "LOW":
        return "Baixo";
      case "MEDIUM":
        return "Médio";
      case "HIGH":
        return "Alto";
      default:
        return level || "N/A";
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Briefcase className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Upload de NFS-e</h1>
            <p className="text-gray-500 mt-1">
              Envie arquivos XML de notas fiscais de serviço para análise
            </p>
          </div>
        </div>
        {nfseNotes.length > 0 && (
          <Button variant="outline" onClick={handleClearAllNotes} className="text-red-600 border-red-200 hover:bg-red-50">
            <Trash2 className="h-4 w-4 mr-2" />
            Limpar {nfseNotes.length} Nota(s)
          </Button>
        )}
      </div>

      {/* Drop Zone */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`
              border-2 border-dashed rounded-xl p-10 text-center transition-all
              ${
                isDragging
                  ? "border-purple-500 bg-purple-50"
                  : "border-gray-300 hover:border-gray-400"
              }
            `}
          >
            <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
              <Upload
                className={`h-8 w-8 ${
                  isDragging ? "text-purple-600" : "text-gray-400"
                }`}
              />
            </div>
            <p className="text-lg font-medium text-gray-900 mb-2">
              Arraste arquivos XML de NFS-e aqui
            </p>
            <p className="text-gray-500 mb-4">ou</p>
            <label>
              <input
                type="file"
                multiple
                accept=".xml,.zip"
                onChange={handleFileInput}
                className="hidden"
              />
              <Button variant="outline" asChild>
                <span className="cursor-pointer">Selecionar Arquivos</span>
              </Button>
            </label>
            <p className="text-xs text-gray-400 mt-4">
              Arquivos XML ABRASF ou ZIP com múltiplas NFS-e
            </p>
          </div>
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">
                Arquivos ({files.length})
              </CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  disabled={isProcessing}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Limpar
                </Button>
                <Button
                  onClick={processFiles}
                  disabled={isProcessing || pendingCount === 0}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processando...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Processar {pendingCount > 0 ? `(${pendingCount})` : ""}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {files.map((fileStatus, index) => (
                <div
                  key={index}
                  className={`
                    flex items-center justify-between p-4 rounded-lg border
                    ${
                      fileStatus.status === "success"
                        ? "bg-green-50 border-green-200"
                        : fileStatus.status === "error"
                        ? "bg-red-50 border-red-200"
                        : fileStatus.status === "processing"
                        ? "bg-purple-50 border-purple-200"
                        : "bg-gray-50 border-gray-200"
                    }
                  `}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`
                        h-10 w-10 rounded-lg flex items-center justify-center
                        ${
                          fileStatus.status === "success"
                            ? "bg-green-100"
                            : fileStatus.status === "error"
                            ? "bg-red-100"
                            : fileStatus.status === "processing"
                            ? "bg-purple-100"
                            : "bg-gray-100"
                        }
                      `}
                    >
                      {fileStatus.status === "success" ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : fileStatus.status === "error" ? (
                        <XCircle className="h-5 w-5 text-red-600" />
                      ) : fileStatus.status === "processing" ? (
                        <Loader2 className="h-5 w-5 text-purple-600 animate-spin" />
                      ) : (
                        <FileText className="h-5 w-5 text-gray-500" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {fileStatus.file.name}
                      </p>
                      {fileStatus.status === "success" && fileStatus.result && (
                        <p className="text-xs text-gray-500">
                          {fileStatus.notesCount && fileStatus.notesCount > 1 
                            ? `${fileStatus.notesCount} notas extraídas`
                            : `${fileStatus.result.prestador?.doc_formatado || "Prestador não identificado"} • ${formatCurrency(fileStatus.result.totals?.valor_servicos)}`
                          }
                        </p>
                      )}
                      {fileStatus.status === "error" && (
                        <p className="text-xs text-red-600">
                          {fileStatus.error}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {fileStatus.status === "success" && fileStatus.result && (
                      <Badge
                        className={getReviewLevelColor(
                          fileStatus.result.document?.review_level || ""
                        )}
                      >
                        {translateReviewLevel(
                          fileStatus.result.document?.review_level || ""
                        )}
                      </Badge>
                    )}
                    {fileStatus.status === "pending" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                      >
                        <XCircle className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Summary */}
            {successCount > 0 && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium text-green-600">
                      {successCount}
                    </span>{" "}
                    nota(s) processada(s) com sucesso
                  </p>
                  <Button 
                    onClick={() => router.push("/nfse/lancamento")}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    Ir para Lançamento
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
