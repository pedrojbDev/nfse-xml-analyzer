"use client";

import { useNotesStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatCurrency,
  translateProductClass,
  translateReviewLevel,
  translateReason,
  getReviewLevelColor,
  getProductClassColor,
  cn,
} from "@/lib/utils";
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  Package,
  Building2,
  Upload,
  XCircle,
  ArrowRight,
  BarChart3,
  MapPin,
} from "lucide-react";
import Link from "next/link";
import { getFilialTypeColor, translateFilialType, FILIAIS } from "@/lib/filiais";
import { NoteFilialInfo } from "@/types/nfe";

export default function DashboardPage() {
  const { notes, getLaunchedNotes, getPendingNotes, getRejectedNotes, getFilialStats } = useNotesStore();

  // Notas por status
  const launchedNotes = getLaunchedNotes();
  const pendingNotes = getPendingNotes();
  const rejectedNotes = getRejectedNotes();

  // Estatísticas APENAS das notas lançadas (para o gestor)
  const launchedStats = {
    total: launchedNotes.length,
    totalValue: launchedNotes.reduce(
      (sum, n) => sum + (n.data.totals?.vNF || 0),
      0
    ),
    highRisk: launchedNotes.filter(
      (n) => n.data.document?.review_level === "HIGH"
    ).length,
    mediumRisk: launchedNotes.filter(
      (n) => n.data.document?.review_level === "MEDIUM"
    ).length,
    lowRisk: launchedNotes.filter(
      (n) => n.data.document?.review_level === "LOW"
    ).length,
    byClass: {
      MEDICAMENTO: launchedNotes.filter(
        (n) => n.data.document?.doc_class === "MEDICAMENTO"
      ).length,
      MATERIAL_HOSPITALAR: launchedNotes.filter(
        (n) => n.data.document?.doc_class === "MATERIAL_HOSPITALAR"
      ).length,
      GENERICO: launchedNotes.filter(
        (n) => n.data.document?.doc_class === "GENERICO"
      ).length,
      MIXED: launchedNotes.filter(
        (n) => n.data.document?.doc_class === "MIXED"
      ).length,
    },
  };

  // Progresso do lançamento
  const progressPercentage = notes.length > 0 
    ? Math.round((launchedNotes.length / notes.length) * 100) 
    : 0;

  // Estatísticas por filial (apenas notas lançadas)
  const filialStatsMap = new Map<number, { 
    filial: NoteFilialInfo; 
    count: number; 
    valor: number; 
    fornecedores: Set<string>;
  }>();

  launchedNotes.forEach((note) => {
    if (!note.filial) return;
    
    const codigo = note.filial.codigo;
    const valor = note.data.totals?.vNF || 0;
    const fornecedor = note.data.emit?.doc || "";
    
    if (filialStatsMap.has(codigo)) {
      const current = filialStatsMap.get(codigo)!;
      current.count += 1;
      current.valor += valor;
      if (fornecedor) current.fornecedores.add(fornecedor);
    } else {
      const fornecedores = new Set<string>();
      if (fornecedor) fornecedores.add(fornecedor);
      filialStatsMap.set(codigo, {
        filial: note.filial,
        count: 1,
        valor,
        fornecedores,
      });
    }
  });

  // Converte para array e ordena por valor
  const filialStats = Array.from(filialStatsMap.values())
    .sort((a, b) => b.valor - a.valor);

  // Se não há notas no sistema
  if (notes.length === 0) {
    return (
      <div className="p-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Painel do Gestor
          </h1>
          <p className="text-gray-500 mt-1">
            Visão geral das notas fiscais lançadas no ERP
          </p>
        </div>

        <Card className="max-w-lg mx-auto mt-20">
          <CardContent className="pt-10 pb-10 text-center">
            <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <Upload className="h-8 w-8 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Nenhuma nota processada
            </h3>
            <p className="text-gray-500 mb-6">
              Faça upload de arquivos XML para começar a análise
            </p>
            <Link href="/upload">
              <Button>
                <Upload className="h-4 w-4 mr-2" />
                Enviar Notas
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Painel do Gestor
          </h1>
          <p className="text-gray-500 mt-1">
            Visão geral das notas fiscais <span className="font-medium text-green-600">lançadas</span> no ERP
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/lancamento">
            <Button variant="outline">
              <Clock className="h-4 w-4 mr-2" />
              Ver Pendentes ({pendingNotes.length})
            </Button>
          </Link>
          <Link href="/upload">
            <Button>
              <Upload className="h-4 w-4 mr-2" />
              Enviar Mais Notas
            </Button>
          </Link>
        </div>
      </div>

      {/* Card de Progresso do Lançamento */}
      <Card className="mb-8 border-2 border-blue-100 bg-gradient-to-r from-blue-50 to-white">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-gray-900">Progresso do Lançamento</h3>
              <p className="text-sm text-gray-500">
                {launchedNotes.length} de {notes.length} notas lançadas
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-blue-600">{progressPercentage}%</p>
              <p className="text-xs text-gray-500">concluído</p>
            </div>
          </div>
          
          {/* Barra de progresso */}
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden mb-4">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-green-500 rounded-full transition-all duration-500"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          
          {/* Status cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <Clock className="h-5 w-5 text-yellow-600" />
              <div>
                <p className="text-lg font-bold text-yellow-700">{pendingNotes.length}</p>
                <p className="text-xs text-yellow-600">Pendentes</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-lg font-bold text-green-700">{launchedNotes.length}</p>
                <p className="text-xs text-green-600">Lançadas</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
              <XCircle className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-lg font-bold text-red-700">{rejectedNotes.length}</p>
                <p className="text-xs text-red-600">Rejeitadas</p>
              </div>
            </div>
          </div>
          
          {pendingNotes.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <Link href="/lancamento">
                <Button variant="outline" className="w-full">
                  <ArrowRight className="h-4 w-4 mr-2" />
                  Continuar Lançamento ({pendingNotes.length} pendentes)
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mensagem se não há notas lançadas ainda */}
      {launchedNotes.length === 0 ? (
        <Card className="mb-8">
          <CardContent className="pt-10 pb-10 text-center">
            <div className="mx-auto w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
              <Clock className="h-8 w-8 text-yellow-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Nenhuma nota lançada ainda
            </h3>
            <p className="text-gray-500 mb-6">
              As estatísticas do gestor aparecerão aqui após as notas serem conferidas e lançadas no ERP.
            </p>
            <Link href="/lancamento">
              <Button>
                <ArrowRight className="h-4 w-4 mr-2" />
                Ir para Conferência
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* KPIs - Apenas notas lançadas */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Notas Lançadas</p>
                    <p className="text-3xl font-bold text-gray-900">{launchedStats.total}</p>
                  </div>
                  <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Valor Total Lançado</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {formatCurrency(launchedStats.totalValue)}
                    </p>
                  </div>
                  <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <TrendingUp className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Risco Alto (Lançadas)</p>
                    <p className="text-3xl font-bold text-red-600">{launchedStats.highRisk}</p>
                  </div>
                  <div className="h-12 w-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <AlertTriangle className="h-6 w-6 text-red-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Risco Baixo (Lançadas)</p>
                    <p className="text-3xl font-bold text-green-600">{launchedStats.lowRisk}</p>
                  </div>
                  <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Distribution by Class */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-blue-600" />
                  Classificação (Lançadas)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(launchedStats.byClass).map(([cls, count]) => (
                    <div key={cls} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`h-3 w-3 rounded-full ${
                            cls === "MEDICAMENTO"
                              ? "bg-blue-500"
                              : cls === "MATERIAL_HOSPITALAR"
                              ? "bg-purple-500"
                              : cls === "MIXED"
                              ? "bg-orange-500"
                              : "bg-gray-400"
                          }`}
                        />
                        <span className="text-sm text-gray-700">
                          {translateProductClass(cls)}
                        </span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {count}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">Distribuição por Nível de Risco (Lançadas)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <div className="flex-1 bg-red-50 rounded-lg p-4 text-center">
                    <p className="text-3xl font-bold text-red-600">{launchedStats.highRisk}</p>
                    <p className="text-sm text-red-700 mt-1">Alto</p>
                    <p className="text-xs text-gray-500 mt-1">Requer atenção</p>
                  </div>
                  <div className="flex-1 bg-yellow-50 rounded-lg p-4 text-center">
                    <p className="text-3xl font-bold text-yellow-600">{launchedStats.mediumRisk}</p>
                    <p className="text-sm text-yellow-700 mt-1">Médio</p>
                    <p className="text-xs text-gray-500 mt-1">Verificar</p>
                  </div>
                  <div className="flex-1 bg-green-50 rounded-lg p-4 text-center">
                    <p className="text-3xl font-bold text-green-600">{launchedStats.lowRisk}</p>
                    <p className="text-sm text-green-700 mt-1">Baixo</p>
                    <p className="text-xs text-gray-500 mt-1">OK</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Estatísticas por Filial */}
          {filialStats.length > 0 && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-blue-600" />
                  Notas por Unidade (Lançadas)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Código</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Unidade</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Tipo</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Localização</th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Notas</th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Fornecedores</th>
                        <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Valor Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filialStats.map((stat, idx) => (
                        <tr 
                          key={stat.filial.codigo} 
                          className="border-b border-gray-100 hover:bg-gray-50"
                        >
                          <td className="py-3 px-4">
                            <span className="font-bold text-blue-700">{stat.filial.codigo}</span>
                          </td>
                          <td className="py-3 px-4">
                            <p className="font-medium text-gray-900 truncate max-w-[200px]" title={stat.filial.nome}>
                              {stat.filial.nome}
                            </p>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="outline" className={getFilialTypeColor(stat.filial.tipo)}>
                              {translateFilialType(stat.filial.tipo)}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-600">
                            {stat.filial.municipio}/{stat.filial.uf}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="font-semibold">{stat.count}</span>
                          </td>
                          <td className="py-3 px-4 text-right text-gray-600">
                            {stat.fornecedores.size}
                          </td>
                          <td className="py-3 px-4 text-right font-semibold text-green-700">
                            {formatCurrency(stat.valor)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-gray-200 bg-gray-50">
                        <td colSpan={4} className="py-3 px-4 font-semibold text-gray-700">
                          Total ({filialStats.length} unidades)
                        </td>
                        <td className="py-3 px-4 text-right font-bold">
                          {filialStats.reduce((sum, s) => sum + s.count, 0)}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-gray-600">
                          {new Set(filialStats.flatMap(s => Array.from(s.fornecedores))).size}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-green-700">
                          {formatCurrency(filialStats.reduce((sum, s) => sum + s.valor, 0))}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Rankings - Apenas notas lançadas */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Top Fornecedores */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-blue-600" />
                  Fornecedores que Mais Receberam (Lançadas)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(() => {
                  // Agrupa por fornecedor - apenas notas lançadas
                  const supplierTotals: Record<string, { name: string; doc: string; total: number; count: number }> = {};
                  launchedNotes.forEach((note) => {
                    const doc = note.data.emit?.doc || "unknown";
                    const name = note.data.emit?.nome || "Não identificado";
                    const value = note.data.totals?.vNF || 0;
                    if (!supplierTotals[doc]) {
                      supplierTotals[doc] = { name, doc, total: 0, count: 0 };
                    }
                    supplierTotals[doc].total += value;
                    supplierTotals[doc].count++;
                  });
                  
                  const sorted = Object.values(supplierTotals)
                    .sort((a, b) => b.total - a.total)
                    .slice(0, 5);

                  if (sorted.length === 0) {
                    return <p className="text-gray-500 text-center py-4">Nenhum fornecedor nas notas lançadas</p>;
                  }

                  const maxTotal = sorted[0]?.total || 1;

                  return (
                    <div className="space-y-4">
                      {sorted.map((supplier, idx) => (
                        <div key={supplier.doc} className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className={`
                                flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
                                ${idx === 0 ? "bg-yellow-100 text-yellow-700" : 
                                  idx === 1 ? "bg-gray-100 text-gray-700" :
                                  idx === 2 ? "bg-orange-100 text-orange-700" :
                                  "bg-gray-50 text-gray-500"}
                              `}>
                                {idx + 1}
                              </span>
                              <div>
                                <p className="text-sm font-medium text-gray-900 truncate max-w-[180px]" title={supplier.name}>
                                  {supplier.name}
                                </p>
                                <p className="text-xs text-gray-500">{supplier.count} nota(s)</p>
                              </div>
                            </div>
                            <p className="text-sm font-semibold text-gray-900">
                              {formatCurrency(supplier.total)}
                            </p>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${
                                idx === 0 ? "bg-blue-500" : 
                                idx === 1 ? "bg-blue-400" :
                                idx === 2 ? "bg-blue-300" :
                                "bg-blue-200"
                              }`}
                              style={{ width: `${(supplier.total / maxTotal) * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </CardContent>
            </Card>

            {/* Top Produtos */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Package className="h-5 w-5 text-green-600" />
                  Produtos Mais Comprados (Lançadas)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(() => {
                  // Agrupa por produto - apenas notas lançadas
                  const productTotals: Record<string, { name: string; code: string; total: number; qty: number; count: number }> = {};
                  
                  launchedNotes.forEach((note) => {
                    const items = note.data.items || [];
                    items.forEach((enrichedItem: any) => {
                      const item = enrichedItem.item || {};
                      const code = item.cProd || "unknown";
                      const name = item.xProd || "Produto não identificado";
                      const value = Number(item.vProd) || 0;
                      const qty = Number(item.qCom) || 0;
                      
                      if (!productTotals[code]) {
                        productTotals[code] = { name, code, total: 0, qty: 0, count: 0 };
                      }
                      productTotals[code].total += value;
                      productTotals[code].qty += qty;
                      productTotals[code].count++;
                    });
                  });
                  
                  const sorted = Object.values(productTotals)
                    .sort((a, b) => b.total - a.total)
                    .slice(0, 5);

                  if (sorted.length === 0) {
                    return (
                      <div className="text-center py-8">
                        <Package className="h-10 w-10 text-gray-300 mx-auto mb-2" />
                        <p className="text-gray-500">Nenhum produto nas notas lançadas</p>
                      </div>
                    );
                  }

                  const maxTotal = sorted[0]?.total || 1;

                  return (
                    <div className="space-y-4">
                      {sorted.map((product, idx) => (
                        <div key={product.code} className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className={`
                                flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
                                ${idx === 0 ? "bg-green-100 text-green-700" : 
                                  idx === 1 ? "bg-gray-100 text-gray-700" :
                                  idx === 2 ? "bg-orange-100 text-orange-700" :
                                  "bg-gray-50 text-gray-500"}
                              `}>
                                {idx + 1}
                              </span>
                              <div>
                                <p className="text-sm font-medium text-gray-900 truncate max-w-[180px]" title={product.name}>
                                  {product.name}
                                </p>
                                <p className="text-xs text-gray-500">
                                  Cód: {product.code} • {product.count}x comprado
                                </p>
                              </div>
                            </div>
                            <p className="text-sm font-semibold text-gray-900">
                              {formatCurrency(product.total)}
                            </p>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${
                                idx === 0 ? "bg-green-500" : 
                                idx === 1 ? "bg-green-400" :
                                idx === 2 ? "bg-green-300" :
                                "bg-green-200"
                              }`}
                              style={{ width: `${(product.total / maxTotal) * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          </div>

          {/* Notes List - Apenas lançadas */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  Notas Lançadas Recentes
                </CardTitle>
                <Link href="/lancamento">
                  <Button variant="outline" size="sm">
                    Ver Todas
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                        Fornecedor
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                        Filial
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                        Número
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                        Valor
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                        Classificação
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                        Lançada em
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {launchedNotes
                      .sort((a, b) => {
                        const dateA = a.launchInfo?.launchedAt ? new Date(a.launchInfo.launchedAt).getTime() : 0;
                        const dateB = b.launchInfo?.launchedAt ? new Date(b.launchInfo.launchedAt).getTime() : 0;
                        return dateB - dateA; // Mais recentes primeiro
                      })
                      .slice(0, 10)
                      .map((note) => (
                        <tr
                          key={note.id}
                          className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              <div className="h-8 w-8 bg-green-100 rounded-lg flex items-center justify-center">
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
                                  {note.data.emit?.nome || "Não identificado"}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {note.data.emit?.doc
                                    ? note.data.emit.doc.replace(
                                        /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
                                        "$1.$2.$3/$4-$5"
                                      )
                                    : "-"}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            {note.filial ? (
                              <div>
                                <p className="text-sm font-medium text-gray-900 truncate max-w-[120px]" title={note.filial.nome}>
                                  {note.filial.nome.length > 15 
                                    ? note.filial.nome.substring(0, 15) + "..." 
                                    : note.filial.nome
                                  }
                                </p>
                                <p className="text-xs text-gray-500">
                                  Cód. {note.filial.codigo} • {note.filial.uf}
                                </p>
                              </div>
                            ) : (
                              <span className="text-xs text-gray-400">N/A</span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <p className="text-sm text-gray-900">
                              {note.data.header?.numero || "-"}/{note.data.header?.serie || "-"}
                            </p>
                            <p className="text-xs text-gray-500">
                              {note.data.header?.data_emissao || "-"}
                            </p>
                          </td>
                          <td className="py-3 px-4">
                            <p className="text-sm font-medium text-gray-900">
                              {formatCurrency(note.data.totals?.vNF)}
                            </p>
                          </td>
                          <td className="py-3 px-4">
                            <Badge
                              className={getProductClassColor(
                                note.data.document?.doc_class || ""
                              )}
                            >
                              {translateProductClass(
                                note.data.document?.doc_class || "UNKNOWN"
                              )}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <p className="text-sm text-gray-600">
                              {note.launchInfo?.launchedAt 
                                ? new Date(note.launchInfo.launchedAt).toLocaleString("pt-BR", {
                                    day: "2-digit",
                                    month: "2-digit",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })
                                : "-"
                              }
                            </p>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
