"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useNfseStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  FileText,
  Building2,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Copy,
  ChevronRight,
  Briefcase,
  Package,
  Calculator,
  ClipboardList,
} from "lucide-react";
import { formatCurrency, cn } from "@/lib/utils";
import { 
  translateServiceClass, 
  translateDocumentClass, 
  getServiceClassColor,
  NfseItem,
} from "@/types/nfse";

export default function NfseLancamentoPage() {
  const router = useRouter();
  const { nfseNotes, selectedNfseId, selectNfse, getSelectedNfse } = useNfseStore();
  const selectedNote = getSelectedNfse();

  // Ordena as notas por número (crescente) e depois por prestador
  const sortedNotes = [...nfseNotes].sort((a, b) => {
    const noteInfoA = (a.data as any)?._noteData || a.data?.summary;
    const noteInfoB = (b.data as any)?._noteData || b.data?.summary;
    const numA = parseInt(noteInfoA?.numero_nota || a.data?.items?.[0]?.fields?.numero_nota || "0", 10);
    const numB = parseInt(noteInfoB?.numero_nota || b.data?.items?.[0]?.fields?.numero_nota || "0", 10);
    
    // Primeiro ordena por número
    if (numA !== numB) return numA - numB;
    
    // Se número igual, ordena por CNPJ do prestador
    const cnpjA = a.data?.prestador?.doc || "";
    const cnpjB = b.data?.prestador?.doc || "";
    return cnpjA.localeCompare(cnpjB);
  });

  // Seleciona primeira nota se nenhuma selecionada
  useEffect(() => {
    if (sortedNotes.length > 0 && !selectedNfseId) {
      selectNfse(sortedNotes[0].id);
    }
  }, [sortedNotes, selectedNfseId, selectNfse]);

  // Redireciona se não houver notas
  if (nfseNotes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="p-4 bg-purple-100 rounded-full mb-4">
          <Briefcase className="h-12 w-12 text-purple-600" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Nenhuma NFS-e Processada
        </h2>
        <p className="text-gray-500 mb-6 text-center max-w-md">
          Faça upload de arquivos XML de NFS-e para começar a conferência e lançamento.
        </p>
        <Button onClick={() => router.push("/nfse/upload")} className="bg-purple-600 hover:bg-purple-700">
          Ir para Upload
        </Button>
      </div>
    );
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getReviewLevelColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "LOW":
        return "bg-green-100 text-green-800 border-green-200";
      case "MEDIUM":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "HIGH":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-600 border-gray-200";
    }
  };

  const translateReviewLevel = (level: string) => {
    switch (level?.toUpperCase()) {
      case "LOW":
        return "Risco Baixo";
      case "MEDIUM":
        return "Risco Médio";
      case "HIGH":
        return "Risco Alto";
      default:
        return level || "N/A";
    }
  };

  const data = selectedNote?.data;
  const document = data?.document;
  const erpProjection = data?.erp_projection;
  const totals = data?.totals;
  const items = data?.items || [];
  const noteData = (data as any)?._noteData;  // Dados específicos da nota individual
  
  // Verifica se é nota cancelada
  const isCancelada = noteData?.is_cancelada || data?.summary?.is_cancelada;

  // Agrupa itens por classe de serviço
  const itemsByClass: Record<string, NfseItem[]> = {};
  items.forEach((item: NfseItem) => {
    const cls = item.normalized?.service_class || "OUTROS";
    if (!itemsByClass[cls]) itemsByClass[cls] = [];
    itemsByClass[cls].push(item);
  });

  // Calcula totais por classe
  const classTotals = Object.entries(itemsByClass).map(([cls, clsItems]) => ({
    class: cls,
    count: clsItems.length,
    total: clsItems.reduce((sum, item) => sum + (item.fields?.valor_total || 0), 0),
  }));
  
  // Dados do serviço (da nota individual)
  const servico = noteData?.servico || items[0]?.fields;

  return (
    <div className="flex h-full">
      {/* Sidebar com lista de notas */}
      <div className="w-80 border-r border-gray-200 bg-white overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-purple-600" />
            NFS-e Processadas
          </h2>
          <p className="text-sm text-gray-500 mt-1">{sortedNotes.length} nota(s) • ordenadas por número</p>
        </div>
        <div className="divide-y divide-gray-100">
          {sortedNotes.map((note, index) => {
            const isSelected = note.id === selectedNfseId;
            const noteDoc = note.data?.document;
            const noteInfo = (note.data as any)?._noteData || note.data?.summary;
            const isNotaCancelada = noteInfo?.is_cancelada;
            const numeroNota = noteInfo?.numero_nota || note.data?.items?.[0]?.fields?.numero_nota;
            const prestadorCnpj = note.data?.prestador?.doc_formatado || "";
            const prestadorNome = note.data?.prestador?.razao_social || note.data?.prestador?.nome || "";
            // Últimos 6 dígitos do CNPJ para identificação rápida
            const cnpjSuffix = prestadorCnpj ? prestadorCnpj.slice(-8) : "";
            
            return (
              <button
                key={note.id}
                onClick={() => selectNfse(note.id)}
                className={cn(
                  "w-full p-3 text-left transition-colors",
                  isSelected ? "bg-purple-50 border-l-4 border-l-purple-600" : "hover:bg-gray-50",
                  isNotaCancelada && "opacity-60"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Número da nota com identificador único */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 font-mono w-6">
                        {(index + 1).toString().padStart(2, '0')}
                      </span>
                      <p className={cn(
                        "font-semibold",
                        isSelected ? "text-purple-900" : "text-gray-900"
                      )}>
                        NF {numeroNota || "S/N"}
                      </p>
                      {isNotaCancelada && (
                        <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
                          Cancelada
                        </Badge>
                      )}
                    </div>
                    
                    {/* Prestador - Nome ou razão social */}
                    <p className="text-sm text-gray-700 truncate mt-1" title={prestadorNome || prestadorCnpj}>
                      {prestadorNome || prestadorCnpj || "Prestador não identificado"}
                    </p>
                    
                    {/* CNPJ e Valor */}
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-gray-400 font-mono">
                        {cnpjSuffix}
                      </span>
                      <span className="text-sm font-semibold text-gray-900">
                        {formatCurrency(note.data?.totals?.valor_servicos)}
                      </span>
                    </div>
                    
                    {/* Badges de classificação */}
                    <div className="flex items-center gap-1 mt-2">
                      <Badge variant="outline" className={cn(
                        "text-xs px-1.5",
                        getServiceClassColor(noteDoc?.doc_class || "")
                      )}>
                        {translateDocumentClass(noteDoc?.doc_class || "N/A")}
                      </Badge>
                      {noteDoc?.review_level && (
                        <Badge variant="outline" className={cn(
                          "text-xs px-1.5",
                          getReviewLevelColor(noteDoc.review_level)
                        )}>
                          {translateReviewLevel(noteDoc.review_level)}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <ChevronRight className={cn(
                    "h-5 w-5 mt-1 flex-shrink-0",
                    isSelected ? "text-purple-600" : "text-gray-400"
                  )} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Conteúdo principal */}
      <div className="flex-1 overflow-y-auto p-6">
        {selectedNote && data ? (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Alerta se nota cancelada */}
            {isCancelada && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
                <AlertTriangle className="h-6 w-6 text-red-600 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-red-800">Nota Cancelada</p>
                  <p className="text-sm text-red-600">
                    Esta nota fiscal foi cancelada e não deve ser lançada no sistema.
                  </p>
                </div>
              </div>
            )}

            {/* Header da nota */}
            <div className={cn(
              "flex items-start justify-between",
              isCancelada && "opacity-60"
            )}>
              <div>
                <div className="flex items-center gap-3">
                  <Badge className={getServiceClassColor(document?.doc_class || "")}>
                    {translateDocumentClass(document?.doc_class || "N/A")}
                  </Badge>
                  <Badge className={getReviewLevelColor(document?.review_level || "")}>
                    {translateReviewLevel(document?.review_level || "")}
                  </Badge>
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mt-2">
                  Nota {noteData?.numero_nota || items[0]?.fields?.numero_nota || "S/N"}
                </h1>
                <p className="text-gray-600 font-medium">
                  {data.prestador?.doc_formatado || "Prestador não identificado"}
                </p>
                <p className="text-gray-500 text-sm">
                  {data.prestador?.nome || data.prestador?.razao_social || ""}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Valor Bruto</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(totals?.valor_servicos)}
                </p>
                {totals?.valor_liquido && (
                  <>
                    <p className="text-sm text-gray-500 mt-1">Valor Líquido</p>
                    <p className="text-lg font-semibold text-green-600">
                      {formatCurrency(totals.valor_liquido)}
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Explicação do sistema */}
            {document?.review_text_ptbr && (
              <Card className="border-l-4 border-l-purple-500">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-purple-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium text-gray-900">Análise do Sistema</p>
                      <p className="text-sm text-gray-600 mt-1">
                        {document.review_text_ptbr}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Tabs */}
            <Tabs defaultValue="dados" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="dados">Dados para Lançamento</TabsTrigger>
                <TabsTrigger value="tributos">Tributos</TabsTrigger>
                <TabsTrigger value="itens">Serviços ({items.length})</TabsTrigger>
                <TabsTrigger value="acoes">Próximas Ações</TabsTrigger>
              </TabsList>

              {/* Tab: Dados para Lançamento */}
              <TabsContent value="dados" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {/* Prestador */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-purple-600" />
                        Prestador
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">CNPJ</span>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{data.prestador?.doc_formatado || "N/A"}</span>
                          {data.prestador?.doc_formatado && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard(data.prestador?.doc || "")}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                      {data.prestador?.nome && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-500">Razão Social</span>
                          <span className="font-medium text-sm">{data.prestador.nome}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Projeção ERP */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Package className="h-4 w-4 text-purple-600" />
                        Projeção para ERP
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Tipo Movimento</span>
                        <Badge variant="outline">{erpProjection?.movement_type || "N/A"}</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Cód. Serviço</span>
                        <Badge variant="outline">{erpProjection?.service_code || "A definir"}</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Valor Bruto</span>
                        <span className="font-medium">{formatCurrency(erpProjection?.valor_bruto)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Valor Líquido</span>
                        <span className="font-medium text-green-600">{formatCurrency(erpProjection?.valor_liquido)}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Informações da Nota */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <FileText className="h-4 w-4 text-purple-600" />
                      Informações da Nota
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm text-gray-500">Número</p>
                        <p className="font-medium">{items[0]?.fields?.numero_nota || "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Competência</p>
                        <p className="font-medium">{items[0]?.fields?.competencia || "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Data Emissão</p>
                        <p className="font-medium">{items[0]?.fields?.data_emissao || "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">CNAE</p>
                        <p className="font-medium">{items[0]?.fields?.cnae || "N/A"}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-sm text-gray-500">Descrição do Serviço</p>
                        <p className="font-medium text-sm">{items[0]?.fields?.descricao_servico || "N/A"}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Tab: Tributos */}
              <TabsContent value="tributos" className="space-y-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Calculator className="h-4 w-4 text-purple-600" />
                      Resumo de Tributos
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">ISS</p>
                        <p className="text-lg font-semibold">{formatCurrency(totals?.valor_iss)}</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">ISS Retido</p>
                        <p className="text-lg font-semibold text-orange-600">{formatCurrency(totals?.valor_iss_retido)}</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">PIS</p>
                        <p className="text-lg font-semibold">{formatCurrency(totals?.valor_pis)}</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">COFINS</p>
                        <p className="text-lg font-semibold">{formatCurrency(totals?.valor_cofins)}</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">INSS</p>
                        <p className="text-lg font-semibold">{formatCurrency(totals?.valor_inss)}</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">IR</p>
                        <p className="text-lg font-semibold">{formatCurrency(totals?.valor_ir)}</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">CSLL</p>
                        <p className="text-lg font-semibold">{formatCurrency(totals?.valor_csll)}</p>
                      </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-gray-200">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-sm text-gray-500">Valor Bruto</p>
                          <p className="text-xl font-bold">{formatCurrency(totals?.valor_servicos)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-gray-500">Valor Líquido</p>
                          <p className="text-xl font-bold text-green-600">{formatCurrency(totals?.valor_liquido)}</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Retenções da Projeção ERP */}
                {erpProjection?.retencoes && Object.keys(erpProjection.retencoes).length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">Retenções a Considerar</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {Object.entries(erpProjection.retencoes).map(([key, value]) => (
                          <div key={key} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                            <span className="text-sm text-gray-600 uppercase">{key.replace("_", " ")}</span>
                            <span className="font-medium text-orange-600">{formatCurrency(value)}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Tab: Serviços/Itens */}
              <TabsContent value="itens" className="space-y-4">
                {/* Resumo por Classificação */}
                {classTotals.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">Resumo por Classificação</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {classTotals.map(({ class: cls, count, total }) => (
                          <div key={cls} className="p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge className={getServiceClassColor(cls)} variant="outline">
                                {translateServiceClass(cls)}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-500">{count} serviço(s)</p>
                            <p className="font-semibold">{formatCurrency(total)}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Lista de Serviços */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Briefcase className="h-4 w-4 text-purple-600" />
                      Serviços da Nota Fiscal
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="text-left py-3 px-2 font-medium text-gray-500">#</th>
                            <th className="text-left py-3 px-2 font-medium text-gray-500">Descrição</th>
                            <th className="text-left py-3 px-2 font-medium text-gray-500">CNAE</th>
                            <th className="text-left py-3 px-2 font-medium text-gray-500">Classificação</th>
                            <th className="text-right py-3 px-2 font-medium text-gray-500">Valor</th>
                            <th className="text-center py-3 px-2 font-medium text-gray-500">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {items.map((item: NfseItem, index: number) => (
                            <tr key={index} className="hover:bg-gray-50">
                              <td className="py-3 px-2 text-gray-500">{index + 1}</td>
                              <td className="py-3 px-2">
                                <div className="max-w-xs truncate" title={item.fields?.descricao_servico || undefined}>
                                  {item.fields?.descricao_servico || "N/A"}
                                </div>
                              </td>
                              <td className="py-3 px-2 font-mono text-xs">
                                {item.fields?.cnae || "N/A"}
                              </td>
                              <td className="py-3 px-2">
                                <Badge className={getServiceClassColor(item.normalized?.service_class || "")} variant="outline">
                                  {translateServiceClass(item.normalized?.service_class || "OUTROS")}
                                </Badge>
                              </td>
                              <td className="py-3 px-2 text-right font-medium">
                                {formatCurrency(item.fields?.valor_total)}
                              </td>
                              <td className="py-3 px-2 text-center">
                                {item.review_level === "LOW" ? (
                                  <CheckCircle className="h-4 w-4 text-green-500 inline" />
                                ) : item.review_level === "MEDIUM" ? (
                                  <AlertTriangle className="h-4 w-4 text-yellow-500 inline" />
                                ) : item.review_level === "HIGH" ? (
                                  <AlertTriangle className="h-4 w-4 text-red-500 inline" />
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="border-t-2 border-gray-200 font-semibold">
                            <td colSpan={4} className="py-3 px-2 text-right">
                              Total dos Serviços:
                            </td>
                            <td className="py-3 px-2 text-right">
                              {formatCurrency(totals?.valor_servicos)}
                            </td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Tab: Próximas Ações */}
              <TabsContent value="acoes" className="space-y-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <ClipboardList className="h-4 w-4 text-purple-600" />
                      Checklist de Conferência
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {document?.next_actions?.map((action: string, index: number) => (
                        <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                          <div className="h-6 w-6 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-medium text-purple-600">{index + 1}</span>
                          </div>
                          <p className="text-sm text-gray-700">{action}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Motivos */}
                {document?.reasons && document.reasons.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">Motivos da Análise</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {document.reasons.map((reason: string, index: number) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {reason}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">Selecione uma nota para ver os detalhes</p>
          </div>
        )}
      </div>
    </div>
  );
}
