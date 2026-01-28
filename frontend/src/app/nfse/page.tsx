"use client";

import { useRouter } from "next/navigation";
import { useNfseStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Briefcase,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Upload,
  TrendingUp,
  Building2,
  FileCheck,
  BarChart3,
} from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";
import { 
  translateServiceClass, 
  translateDocumentClass, 
  getServiceClassColor,
  NfseItem,
} from "@/types/nfse";

export default function NfseDashboardPage() {
  const router = useRouter();
  const { nfseNotes } = useNfseStore();

  // Calcula estatísticas
  const totalNotas = nfseNotes.length;
  const totalValorServicos = nfseNotes.reduce(
    (sum, note) => sum + (note.data?.totals?.valor_servicos || 0),
    0
  );
  const totalValorLiquido = nfseNotes.reduce(
    (sum, note) => sum + (note.data?.totals?.valor_liquido || 0),
    0
  );

  // Conta por nível de risco
  const riskCounts = nfseNotes.reduce(
    (acc, note) => {
      const level = note.data?.document?.review_level?.toUpperCase() || "UNKNOWN";
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  // Conta por classe de documento
  const classCounts = nfseNotes.reduce(
    (acc, note) => {
      const cls = note.data?.document?.doc_class || "UNKNOWN";
      acc[cls] = (acc[cls] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  // Top prestadores
  const prestadorTotals: Record<string, { nome: string; total: number; count: number }> = {};
  nfseNotes.forEach((note) => {
    const cnpj = note.data?.prestador?.doc || "unknown";
    const nome = note.data?.prestador?.doc_formatado || note.data?.prestador?.nome || cnpj;
    const valor = note.data?.totals?.valor_servicos || 0;
    
    if (!prestadorTotals[cnpj]) {
      prestadorTotals[cnpj] = { nome, total: 0, count: 0 };
    }
    prestadorTotals[cnpj].total += valor;
    prestadorTotals[cnpj].count += 1;
  });
  
  const topPrestadores = Object.entries(prestadorTotals)
    .sort(([, a], [, b]) => b.total - a.total)
    .slice(0, 5);

  // Top tipos de serviço
  const serviceTotals: Record<string, { total: number; count: number }> = {};
  nfseNotes.forEach((note) => {
    const items = note.data?.items || [];
    items.forEach((item: NfseItem) => {
      const cls = item.normalized?.service_class || "OUTROS";
      if (!serviceTotals[cls]) {
        serviceTotals[cls] = { total: 0, count: 0 };
      }
      serviceTotals[cls].total += item.fields?.valor_total || 0;
      serviceTotals[cls].count += 1;
    });
  });
  
  const topServicos = Object.entries(serviceTotals)
    .sort(([, a], [, b]) => b.total - a.total)
    .slice(0, 5);

  const maxPrestadorValue = topPrestadores.length > 0 ? topPrestadores[0][1].total : 1;
  const maxServicoValue = topServicos.length > 0 ? topServicos[0][1].total : 1;

  if (totalNotas === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="p-4 bg-purple-100 rounded-full mb-4">
          <Briefcase className="h-12 w-12 text-purple-600" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Nenhuma NFS-e Processada
        </h2>
        <p className="text-gray-500 mb-6 text-center max-w-md">
          Faça upload de arquivos XML de NFS-e para ver o painel com estatísticas e análises.
        </p>
        <Button onClick={() => router.push("/nfse/upload")} className="bg-purple-600 hover:bg-purple-700">
          <Upload className="h-4 w-4 mr-2" />
          Fazer Upload
        </Button>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Briefcase className="h-6 w-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Painel NFS-e</h1>
            <p className="text-gray-500">Visão geral das notas de serviço</p>
          </div>
        </div>
        <Button onClick={() => router.push("/nfse/upload")} className="bg-purple-600 hover:bg-purple-700">
          <Upload className="h-4 w-4 mr-2" />
          Novo Upload
        </Button>
      </div>

      {/* Cards de estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total de Notas</p>
                <p className="text-3xl font-bold text-gray-900">{totalNotas}</p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <FileCheck className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Valor Total (Bruto)</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalValorServicos)}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <DollarSign className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Valor Líquido</p>
                <p className="text-2xl font-bold text-green-600">{formatCurrency(totalValorLiquido)}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Risco Alto</p>
                <p className="text-3xl font-bold text-red-600">{riskCounts["HIGH"] || 0}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-full">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Distribuição por risco e classe */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Por nível de risco */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-purple-600" />
              Distribuição por Risco
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm">Risco Baixo</span>
                </div>
                <Badge className="bg-green-100 text-green-800">{riskCounts["LOW"] || 0}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm">Risco Médio</span>
                </div>
                <Badge className="bg-yellow-100 text-yellow-800">{riskCounts["MEDIUM"] || 0}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <span className="text-sm">Risco Alto</span>
                </div>
                <Badge className="bg-red-100 text-red-800">{riskCounts["HIGH"] || 0}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Por classe de documento */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-purple-600" />
              Distribuição por Tipo
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(classCounts).map(([cls, count]) => (
                <div key={cls} className="flex items-center justify-between">
                  <span className="text-sm">{translateDocumentClass(cls)}</span>
                  <Badge className={getServiceClassColor(cls)}>{count}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Rankings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Prestadores */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-purple-600" />
              Prestadores que Mais Receberam
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topPrestadores.length > 0 ? (
              <div className="space-y-4">
                {topPrestadores.map(([cnpj, data], index) => (
                  <div key={cnpj} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-500 w-5">{index + 1}.</span>
                        <span className="text-sm font-medium truncate max-w-[200px]">{data.nome}</span>
                      </div>
                      <span className="text-sm font-semibold text-purple-600">
                        {formatCurrency(data.total)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-purple-500 h-2 rounded-full transition-all"
                          style={{ width: `${(data.total / maxPrestadorValue) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-16 text-right">{data.count} nota(s)</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                Nenhum prestador identificado
              </p>
            )}
          </CardContent>
        </Card>

        {/* Top Tipos de Serviço */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-purple-600" />
              Tipos de Serviço Mais Contratados
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topServicos.length > 0 ? (
              <div className="space-y-4">
                {topServicos.map(([cls, data], index) => (
                  <div key={cls} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-500 w-5">{index + 1}.</span>
                        <Badge className={cn(getServiceClassColor(cls), "font-normal")}>
                          {translateServiceClass(cls)}
                        </Badge>
                      </div>
                      <span className="text-sm font-semibold text-purple-600">
                        {formatCurrency(data.total)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-purple-500 h-2 rounded-full transition-all"
                          style={{ width: `${(data.total / maxServicoValue) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-20 text-right">{data.count} serviço(s)</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                Nenhum serviço identificado
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Notas Recentes */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Notas por Número (Ordenadas)</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => router.push("/nfse/lancamento")}>
              Ver todas
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-2 font-medium text-gray-500">Nº Nota</th>
                  <th className="text-left py-3 px-2 font-medium text-gray-500">Prestador</th>
                  <th className="text-left py-3 px-2 font-medium text-gray-500">Tipo</th>
                  <th className="text-right py-3 px-2 font-medium text-gray-500">Valor Bruto</th>
                  <th className="text-right py-3 px-2 font-medium text-gray-500">Valor Líquido</th>
                  <th className="text-center py-3 px-2 font-medium text-gray-500">Risco</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[...nfseNotes]
                  .sort((a, b) => {
                    const noteInfoA = (a.data as any)?._noteData || a.data?.summary;
                    const noteInfoB = (b.data as any)?._noteData || b.data?.summary;
                    const numA = parseInt(noteInfoA?.numero_nota || a.data?.items?.[0]?.fields?.numero_nota || "0", 10);
                    const numB = parseInt(noteInfoB?.numero_nota || b.data?.items?.[0]?.fields?.numero_nota || "0", 10);
                    return numA - numB;
                  })
                  .slice(0, 10)
                  .map((note) => {
                    const noteInfo = (note.data as any)?._noteData || note.data?.summary;
                    const numeroNota = noteInfo?.numero_nota || note.data?.items?.[0]?.fields?.numero_nota;
                    return (
                      <tr key={note.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => router.push("/nfse/lancamento")}>
                        <td className="py-3 px-2">
                          <p className="font-semibold text-gray-900">
                            {numeroNota || "S/N"}
                          </p>
                        </td>
                        <td className="py-3 px-2">
                          <p className="font-medium truncate max-w-[180px]" title={note.data?.prestador?.doc_formatado || ""}>
                            {note.data?.prestador?.razao_social || note.data?.prestador?.nome || note.data?.prestador?.doc_formatado || "N/A"}
                          </p>
                          <p className="text-xs text-gray-400 font-mono">
                            {note.data?.prestador?.doc_formatado?.slice(-8) || ""}
                          </p>
                        </td>
                        <td className="py-3 px-2">
                          <Badge className={getServiceClassColor(note.data?.document?.doc_class || "")} variant="outline">
                            {translateDocumentClass(note.data?.document?.doc_class || "N/A")}
                          </Badge>
                        </td>
                        <td className="py-3 px-2 text-right font-medium">
                          {formatCurrency(note.data?.totals?.valor_servicos)}
                        </td>
                        <td className="py-3 px-2 text-right font-medium text-green-600">
                          {formatCurrency(note.data?.totals?.valor_liquido)}
                        </td>
                        <td className="py-3 px-2 text-center">
                          {note.data?.document?.review_level === "LOW" ? (
                            <CheckCircle className="h-4 w-4 text-green-500 inline" />
                          ) : note.data?.document?.review_level === "MEDIUM" ? (
                            <AlertTriangle className="h-4 w-4 text-yellow-500 inline" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-red-500 inline" />
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
