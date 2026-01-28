"use client";

import { useState } from "react";
import { useNotesStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
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
  Building2,
  Calendar,
  Hash,
  Package,
  AlertCircle,
  CheckCircle2,
  Copy,
  Download,
  ArrowRight,
  Banknote,
  Truck,
  ClipboardList,
  Info,
  Clock,
  XCircle,
  Send,
  RotateCcw,
  MapPin,
} from "lucide-react";
import Link from "next/link";
import { NoteLaunchStatus, NoteFilialInfo } from "@/types/nfe";
import { getFilialTypeColor, translateFilialType } from "@/lib/filiais";

// Tradução de status de lançamento
function translateLaunchStatus(status: NoteLaunchStatus | undefined): string {
  switch (status) {
    case "launched":
      return "Lançada";
    case "rejected":
      return "Rejeitada";
    case "pending":
    default:
      return "Pendente";
  }
}

// Cor do badge de status
function getLaunchStatusColor(status: NoteLaunchStatus | undefined): string {
  switch (status) {
    case "launched":
      return "bg-green-100 text-green-800 border-green-200";
    case "rejected":
      return "bg-red-100 text-red-800 border-red-200";
    case "pending":
    default:
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
  }
}

// Ícone do status
function LaunchStatusIcon({ status }: { status: NoteLaunchStatus | undefined }) {
  switch (status) {
    case "launched":
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case "rejected":
      return <XCircle className="h-4 w-4 text-red-600" />;
    case "pending":
    default:
      return <Clock className="h-4 w-4 text-yellow-600" />;
  }
}

export default function LancamentoPage() {
  const { 
    notes, 
    selectedNoteId, 
    selectNote, 
    markAsLaunched, 
    markAsRejected,
    resetLaunchStatus,
    getPendingNotes,
    getLaunchedNotes,
    getRejectedNotes,
  } = useNotesStore();
  
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "pending" | "launched" | "rejected">("pending");
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [launchNotes, setLaunchNotes] = useState("");

  const selectedNote = notes.find((n) => n.id === selectedNoteId);

  // Filtra notas por status
  const filteredNotes = (() => {
    switch (statusFilter) {
      case "pending":
        return getPendingNotes();
      case "launched":
        return getLaunchedNotes();
      case "rejected":
        return getRejectedNotes();
      default:
        return notes;
    }
  })();

  // Contadores
  const pendingCount = getPendingNotes().length;
  const launchedCount = getLaunchedNotes().length;
  const rejectedCount = getRejectedNotes().length;

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  // Se não há nota selecionada, seleciona a primeira da lista filtrada
  if (!selectedNote && filteredNotes.length > 0) {
    selectNote(filteredNotes[0].id);
    return null;
  }

  // Handlers de lançamento
  const handleMarkAsLaunched = () => {
    if (selectedNote) {
      markAsLaunched(selectedNote.id, undefined, launchNotes || undefined);
      setLaunchNotes("");
      // Seleciona a próxima nota pendente
      const pending = getPendingNotes().filter(n => n.id !== selectedNote.id);
      if (pending.length > 0) {
        selectNote(pending[0].id);
      }
    }
  };

  const handleMarkAsRejected = () => {
    if (selectedNote && rejectReason.trim()) {
      markAsRejected(selectedNote.id, rejectReason);
      setRejectReason("");
      setShowRejectModal(false);
      // Seleciona a próxima nota pendente
      const pending = getPendingNotes().filter(n => n.id !== selectedNote.id);
      if (pending.length > 0) {
        selectNote(pending[0].id);
      }
    }
  };

  const handleResetStatus = () => {
    if (selectedNote) {
      resetLaunchStatus(selectedNote.id);
    }
  };

  if (notes.length === 0) {
    return (
      <div className="p-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Conferência e Lançamento
          </h1>
          <p className="text-gray-500 mt-1">
            Visualize os dados completos para lançamento no ERP
          </p>
        </div>

        <Card className="max-w-lg mx-auto mt-20">
          <CardContent className="pt-10 pb-10 text-center">
            <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
              <FileText className="h-8 w-8 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Nenhuma nota para lançar
            </h3>
            <p className="text-gray-500 mb-6">
              Faça upload de arquivos XML para começar
            </p>
            <Link href="/upload">
              <Button>Enviar Notas</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const data = selectedNote?.data;
  const doc = data?.document;
  const erp = data?.erp_projection;
  const header = data?.header;
  const emit = data?.emit;
  const dest = data?.dest;
  const totals = data?.totals;
  const launchInfo = selectedNote?.launchInfo;
  const currentStatus = launchInfo?.status || "pending";
  const filial = selectedNote?.filial;

  return (
    <div className="flex h-full">
      {/* Sidebar - Lista de Notas */}
      <div className="w-80 border-r border-gray-200 bg-white overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Notas para Conferência</h2>
          <p className="text-xs text-gray-500 mt-1">{notes.length} nota(s) total</p>
          
          {/* Filtro por Status */}
          <div className="mt-3 flex flex-wrap gap-1">
            <button
              onClick={() => setStatusFilter("pending")}
              className={cn(
                "px-2 py-1 text-xs rounded-full border transition-colors",
                statusFilter === "pending"
                  ? "bg-yellow-100 border-yellow-300 text-yellow-800"
                  : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
              )}
            >
              Pendentes ({pendingCount})
            </button>
            <button
              onClick={() => setStatusFilter("launched")}
              className={cn(
                "px-2 py-1 text-xs rounded-full border transition-colors",
                statusFilter === "launched"
                  ? "bg-green-100 border-green-300 text-green-800"
                  : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
              )}
            >
              Lançadas ({launchedCount})
            </button>
            <button
              onClick={() => setStatusFilter("rejected")}
              className={cn(
                "px-2 py-1 text-xs rounded-full border transition-colors",
                statusFilter === "rejected"
                  ? "bg-red-100 border-red-300 text-red-800"
                  : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
              )}
            >
              Rejeitadas ({rejectedCount})
            </button>
            <button
              onClick={() => setStatusFilter("all")}
              className={cn(
                "px-2 py-1 text-xs rounded-full border transition-colors",
                statusFilter === "all"
                  ? "bg-blue-100 border-blue-300 text-blue-800"
                  : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
              )}
            >
              Todas ({notes.length})
            </button>
          </div>
        </div>
        
        <div className="divide-y divide-gray-100">
          {filteredNotes.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm text-gray-500">
                Nenhuma nota com este status
              </p>
            </div>
          ) : (
            filteredNotes.map((note) => {
              const noteStatus = note.launchInfo?.status || "pending";
              const noteFilial = note.filial;
              return (
                <button
                  key={note.id}
                  onClick={() => selectNote(note.id)}
                  className={cn(
                    "w-full p-4 text-left hover:bg-gray-50 transition-colors",
                    selectedNoteId === note.id && "bg-blue-50 border-l-4 border-blue-500"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {/* Status + Fornecedor */}
                      <div className="flex items-center gap-2 mb-1">
                        <LaunchStatusIcon status={noteStatus} />
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {note.data.emit?.nome || "Fornecedor não identificado"}
                        </p>
                      </div>
                      <p className="text-xs text-gray-500 ml-6">
                        Nota {note.data.header?.numero}/{note.data.header?.serie}
                      </p>
                      {/* Filial */}
                      {noteFilial && (
                        <div className="flex items-center gap-1 ml-6 mt-1">
                          <MapPin className="h-3 w-3 text-gray-400" />
                          <span className="text-xs text-gray-600 truncate" title={noteFilial.nome}>
                            {noteFilial.nome.length > 20 
                              ? noteFilial.nome.substring(0, 20) + "..." 
                              : noteFilial.nome
                            }
                          </span>
                        </div>
                      )}
                      <div className="flex items-center justify-between mt-2 ml-6">
                        <p className="text-sm font-semibold text-gray-900">
                          {formatCurrency(note.data.totals?.vNF)}
                        </p>
                        <Badge
                          variant="outline"
                          className={cn("text-xs", getLaunchStatusColor(noteStatus))}
                        >
                          {translateLaunchStatus(noteStatus)}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {selectedNote && data ? (
          <div className="p-8">
            {/* Header com Status */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-2xl font-bold text-gray-900">
                    Nota {header?.numero}/{header?.serie}
                  </h1>
                  <Badge className={getProductClassColor(doc?.doc_class || "")}>
                    {translateProductClass(doc?.doc_class || "")}
                  </Badge>
                  <Badge className={getReviewLevelColor(doc?.review_level || "")}>
                    Risco {translateReviewLevel(doc?.review_level || "")}
                  </Badge>
                  <Badge variant="outline" className={getLaunchStatusColor(currentStatus)}>
                    {translateLaunchStatus(currentStatus)}
                  </Badge>
                </div>
                <p className="text-gray-500">{emit?.nome}</p>
                
                {/* Informação da Filial */}
                {filial && (
                  <div className="flex items-center gap-2 mt-2">
                    <MapPin className="h-4 w-4 text-blue-600" />
                    <Badge variant="outline" className={getFilialTypeColor(filial.tipo)}>
                      {translateFilialType(filial.tipo)}
                    </Badge>
                    <span className="text-sm font-medium text-gray-700">
                      {filial.nome}
                    </span>
                    <span className="text-xs text-gray-500">
                      ({filial.municipio}/{filial.uf})
                    </span>
                  </div>
                )}
                {!filial && dest?.doc && (
                  <div className="flex items-center gap-2 mt-2">
                    <MapPin className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-500">
                      Filial não identificada (CNPJ: {dest.doc})
                    </span>
                  </div>
                )}
                
                {/* Info de lançamento se já foi lançada */}
                {currentStatus === "launched" && launchInfo?.launchedAt && (
                  <p className="text-xs text-green-600 mt-1">
                    Lançada em {new Date(launchInfo.launchedAt).toLocaleString("pt-BR")}
                    {launchInfo.launchedBy && ` por ${launchInfo.launchedBy}`}
                  </p>
                )}
                {currentStatus === "rejected" && launchInfo?.rejectedAt && (
                  <p className="text-xs text-red-600 mt-1">
                    Rejeitada em {new Date(launchInfo.rejectedAt).toLocaleString("pt-BR")}
                    {launchInfo.rejectionReason && `: ${launchInfo.rejectionReason}`}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  Exportar
                </Button>
              </div>
            </div>

            {/* Alert de Pendências */}
            {doc?.review_level !== "LOW" && currentStatus === "pending" && (
              <div className={cn(
                "rounded-lg p-4 mb-6",
                doc?.review_level === "HIGH" ? "bg-red-50 border border-red-200" : "bg-yellow-50 border border-yellow-200"
              )}>
                <div className="flex items-start gap-3">
                  <AlertCircle className={cn(
                    "h-5 w-5 mt-0.5",
                    doc?.review_level === "HIGH" ? "text-red-600" : "text-yellow-600"
                  )} />
                  <div>
                    <p className={cn(
                      "font-medium",
                      doc?.review_level === "HIGH" ? "text-red-800" : "text-yellow-800"
                    )}>
                      {doc?.review_level === "HIGH" ? "Atenção Necessária" : "Verificação Recomendada"}
                    </p>
                    <p className={cn(
                      "text-sm mt-1",
                      doc?.review_level === "HIGH" ? "text-red-700" : "text-yellow-700"
                    )}>
                      {doc?.review_text_ptbr}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Tabs com conteúdo */}
            <Tabs defaultValue="dados" className="space-y-6">
              <TabsList>
                <TabsTrigger value="dados">Dados para Lançamento</TabsTrigger>
                <TabsTrigger value="itens">Itens ({data?.items?.length || 0})</TabsTrigger>
                <TabsTrigger value="fornecedor">Fornecedor</TabsTrigger>
                <TabsTrigger value="valores">Valores e Impostos</TabsTrigger>
                <TabsTrigger value="pendencias">Pendências</TabsTrigger>
              </TabsList>

              {/* Tab: Dados para Lançamento */}
              <TabsContent value="dados" className="space-y-6">
                {/* Card Filial - Destaque */}
                <Card className={cn(
                  "border-2",
                  filial ? "border-blue-200 bg-blue-50/50" : "border-gray-200"
                )}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <MapPin className="h-5 w-5 text-blue-600" />
                      Unidade Destinatária
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {filial ? (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-medium">Código RM</p>
                          <p className="text-lg font-bold text-blue-700">{filial.codigo}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-medium">Unidade</p>
                          <p className="font-semibold text-gray-900">{filial.nome}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-medium">Localização</p>
                          <p className="text-gray-700">{filial.municipio}/{filial.uf}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-medium">Tipo</p>
                          <Badge variant="outline" className={getFilialTypeColor(filial.tipo)}>
                            {translateFilialType(filial.tipo)}
                          </Badge>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 text-gray-500">
                        <AlertCircle className="h-5 w-5" />
                        <div>
                          <p className="font-medium">Filial não identificada</p>
                          <p className="text-sm">O CNPJ do destinatário ({dest?.doc || "N/A"}) não corresponde a nenhuma unidade cadastrada.</p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Card Principal - Dados Essenciais */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <ClipboardList className="h-5 w-5 text-blue-600" />
                      Dados Essenciais para o ERP
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-6">
                      {/* Coluna 1 */}
                      <div className="space-y-4">
                        <DataField
                          label="Código da Filial"
                          value={filial ? String(filial.codigo) : "-"}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                          icon={<MapPin className="h-4 w-4" />}
                          highlight
                        />
                        <DataField
                          label="Tipo de Movimento"
                          value={erp?.movement_type || "1.2.01"}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                          icon={<ArrowRight className="h-4 w-4" />}
                        />
                        <DataField
                          label="Código do Produto"
                          value={erp?.product_code || "-"}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                          icon={<Package className="h-4 w-4" />}
                        />
                        <DataField
                          label="Número da Nota"
                          value={String(header?.numero || "")}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                          icon={<Hash className="h-4 w-4" />}
                        />
                      </div>

                      {/* Coluna 2 */}
                      <div className="space-y-4">
                        <DataField
                          label="Série"
                          value={String(header?.serie || "")}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                        />
                        <DataField
                          label="Data de Emissão"
                          value={header?.data_emissao || "-"}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                          icon={<Calendar className="h-4 w-4" />}
                        />
                        <DataField
                          label="Valor Total"
                          value={formatCurrency(totals?.vNF)}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                          highlight
                          icon={<Banknote className="h-4 w-4" />}
                          highlight
                        />
                        <DataField
                          label="Condição de Pagamento"
                          value={erp?.payment_hint || "BOLETO"}
                          onCopy={copyToClipboard}
                          copied={copiedField}
                        />
                        <DataField
                          label="Status Sugerido"
                          value="PENDENTE"
                          onCopy={copyToClipboard}
                          copied={copiedField}
                        />
                      </div>
                    </div>

                    <Separator className="my-6" />

                    {/* Chave de Acesso */}
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Chave de Acesso (44 dígitos)
                      </label>
                      <div className="mt-2 flex items-center gap-2">
                        <code className="flex-1 bg-gray-100 px-4 py-3 rounded-lg text-sm font-mono text-gray-800 break-all">
                          {header?.chave_nfe || "-"}
                        </code>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            copyToClipboard(header?.chave_nfe || "", "chave")
                          }
                        >
                          {copiedField === "chave" ? (
                            <CheckCircle2 className="h-4 w-4 text-green-600" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Próximas Ações */}
                {doc?.next_actions && doc.next_actions.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Info className="h-5 w-5 text-blue-600" />
                        Próximos Passos
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ol className="space-y-3">
                        {doc.next_actions.map((action, idx) => (
                          <li key={idx} className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-medium">
                              {idx + 1}
                            </span>
                            <span className="text-gray-700">{action}</span>
                          </li>
                        ))}
                      </ol>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* Tab: Itens */}
              <TabsContent value="itens" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Package className="h-5 w-5 text-blue-600" />
                      Itens da Nota Fiscal
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {data?.items && data.items.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="text-left py-3 px-4 font-medium text-gray-500">#</th>
                              <th className="text-left py-3 px-4 font-medium text-gray-500">Produto</th>
                              <th className="text-left py-3 px-4 font-medium text-gray-500">NCM</th>
                              <th className="text-left py-3 px-4 font-medium text-gray-500">Classificação</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-500">Qtd</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-500">Valor Unit.</th>
                              <th className="text-right py-3 px-4 font-medium text-gray-500">Total</th>
                              <th className="text-center py-3 px-4 font-medium text-gray-500">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {data.items.map((enrichedItem, idx) => {
                              const item = enrichedItem.item || {};
                              const normalized = enrichedItem.normalized || {};
                              return (
                                <tr key={idx} className="hover:bg-gray-50">
                                  <td className="py-3 px-4 text-gray-600">{item.nItem || idx + 1}</td>
                                  <td className="py-3 px-4">
                                    <div>
                                      <p className="font-medium text-gray-900 truncate max-w-xs" title={item.xProd || undefined}>
                                        {item.xProd || "-"}
                                      </p>
                                      <p className="text-xs text-gray-500">Cód: {item.cProd || "-"}</p>
                                    </div>
                                  </td>
                                  <td className="py-3 px-4 text-gray-600 font-mono text-xs">{item.NCM || "-"}</td>
                                  <td className="py-3 px-4">
                                    <Badge className={getProductClassColor(normalized.product_class || "")}>
                                      {translateProductClass(normalized.product_class || "UNKNOWN")}
                                    </Badge>
                                  </td>
                                  <td className="py-3 px-4 text-right text-gray-600">
                                    {item.qCom?.toLocaleString("pt-BR")} {item.uCom || ""}
                                  </td>
                                  <td className="py-3 px-4 text-right text-gray-600">
                                    {formatCurrency(item.vUnCom)}
                                  </td>
                                  <td className="py-3 px-4 text-right font-medium text-gray-900">
                                    {formatCurrency(item.vProd)}
                                  </td>
                                  <td className="py-3 px-4 text-center">
                                    <Badge className={getReviewLevelColor(enrichedItem.review_level || "")}>
                                      {translateReviewLevel(enrichedItem.review_level || "")}
                                    </Badge>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                          <tfoot>
                            <tr className="border-t-2 border-gray-200 bg-gray-50">
                              <td colSpan={6} className="py-3 px-4 text-right font-medium text-gray-700">
                                Total dos Produtos:
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-gray-900">
                                {formatCurrency(totals?.vProd)}
                              </td>
                              <td></td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <Package className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-500">Nenhum item disponível</p>
                        <p className="text-xs text-gray-400 mt-1">
                          Os itens serão exibidos quando disponíveis na nota
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Tab: Fornecedor */}
              <TabsContent value="fornecedor" className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  {/* Emitente */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Building2 className="h-5 w-5 text-blue-600" />
                        Fornecedor (Emitente)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <DataField
                        label="Razão Social"
                        value={emit?.nome || "-"}
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                      <DataField
                        label="CNPJ"
                        value={
                          emit?.doc
                            ? emit.doc.replace(
                                /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
                                "$1.$2.$3/$4-$5"
                              )
                            : "-"
                        }
                        onCopy={copyToClipboard}
                        copied={copiedField}
                        highlight
                      />
                      <DataField
                        label="UF"
                        value={emit?.uf || "-"}
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                      <DataField
                        label="Município"
                        value={emit?.municipio || "-"}
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                    </CardContent>
                  </Card>

                  {/* Destinatário */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Truck className="h-5 w-5 text-green-600" />
                        Destinatário
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <DataField
                        label="Razão Social"
                        value={dest?.nome || "-"}
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                      <DataField
                        label="CNPJ"
                        value={
                          dest?.doc
                            ? dest.doc.replace(
                                /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
                                "$1.$2.$3/$4-$5"
                              )
                            : "-"
                        }
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                      <DataField
                        label="UF"
                        value={dest?.uf || "-"}
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                      <DataField
                        label="Município"
                        value={dest?.municipio || "-"}
                        onCopy={copyToClipboard}
                        copied={copiedField}
                      />
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              {/* Tab: Valores */}
              <TabsContent value="valores" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Banknote className="h-5 w-5 text-green-600" />
                      Totais da Nota
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                      <ValueCard
                        label="Valor Total da Nota"
                        value={totals?.vNF}
                        highlight
                      />
                      <ValueCard label="Valor dos Produtos" value={totals?.vProd} />
                      <ValueCard label="Desconto" value={totals?.vDesc} />
                      <ValueCard label="Frete" value={totals?.vFrete} />
                      <ValueCard label="Outras Despesas" value={totals?.vOutro} />
                    </div>

                    <Separator className="my-6" />

                    <h4 className="font-medium text-gray-900 mb-4">Impostos</h4>
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                      <ValueCard label="ICMS" value={totals?.vICMS} />
                      <ValueCard label="ICMS ST" value={totals?.vICMSST} />
                      <ValueCard label="IPI" value={totals?.vIPI} />
                      <ValueCard label="PIS" value={totals?.vPIS} />
                      <ValueCard label="COFINS" value={totals?.vCOFINS} />
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Tab: Pendências */}
              <TabsContent value="pendencias" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-yellow-600" />
                      Motivos de Revisão
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {doc?.reasons && doc.reasons.length > 0 ? (
                      <div className="space-y-3">
                        {doc.reasons.map((reason, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
                          >
                            <div className="h-6 w-6 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
                              <span className="text-xs font-medium text-yellow-700">
                                {idx + 1}
                              </span>
                            </div>
                            <div>
                              <p className="font-medium text-gray-900">
                                {translateReason(reason)}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                Código: {reason}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-3" />
                        <p className="text-gray-600">
                          Nenhuma pendência identificada
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Qualidade dos Dados */}
                {doc?.quality && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">
                        Qualidade dos Dados
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-3 gap-4">
                        <div className="text-center p-4 bg-red-50 rounded-lg">
                          <p className="text-2xl font-bold text-red-600">
                            {doc.quality.items_review_high}
                          </p>
                          <p className="text-sm text-red-700">Itens Críticos</p>
                        </div>
                        <div className="text-center p-4 bg-yellow-50 rounded-lg">
                          <p className="text-2xl font-bold text-yellow-600">
                            {doc.quality.items_review_medium}
                          </p>
                          <p className="text-sm text-yellow-700">
                            Itens com Alerta
                          </p>
                        </div>
                        <div className="text-center p-4 bg-gray-50 rounded-lg">
                          <p className="text-2xl font-bold text-gray-600">
                            {doc.quality.items_incomplete}
                          </p>
                          <p className="text-sm text-gray-700">
                            Itens Incompletos
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>

            {/* ============================================== */}
            {/* SEÇÃO DE AÇÕES DE LANÇAMENTO */}
            {/* ============================================== */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              {currentStatus === "pending" ? (
                <Card className="border-2 border-blue-200 bg-blue-50">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2 text-blue-800">
                      <Send className="h-5 w-5" />
                      Confirmar Lançamento no ERP
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-blue-700 mb-4">
                      Após conferir todos os dados acima e lançar a nota no sistema ERP, 
                      clique no botão abaixo para marcar esta nota como lançada.
                    </p>
                    
                    {/* Campo de observações opcional */}
                    <div className="mb-4">
                      <label className="text-sm font-medium text-gray-700 block mb-2">
                        Observações (opcional)
                      </label>
                      <textarea
                        value={launchNotes}
                        onChange={(e) => setLaunchNotes(e.target.value)}
                        placeholder="Adicione observações sobre o lançamento..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={2}
                      />
                    </div>

                    <div className="flex gap-3">
                      <Button 
                        onClick={handleMarkAsLaunched}
                        className="flex-1 bg-green-600 hover:bg-green-700"
                      >
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        Marcar como Lançada
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => setShowRejectModal(true)}
                        className="text-red-600 border-red-300 hover:bg-red-50"
                      >
                        <XCircle className="h-4 w-4 mr-2" />
                        Rejeitar
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : currentStatus === "launched" ? (
                <Card className="border-2 border-green-200 bg-green-50">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-100 rounded-full">
                          <CheckCircle2 className="h-6 w-6 text-green-600" />
                        </div>
                        <div>
                          <p className="font-semibold text-green-800">Nota Lançada com Sucesso</p>
                          <p className="text-sm text-green-600">
                            {launchInfo?.launchedAt && 
                              `Lançada em ${new Date(launchInfo.launchedAt).toLocaleString("pt-BR")}`
                            }
                            {launchInfo?.notes && ` • ${launchInfo.notes}`}
                          </p>
                        </div>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={handleResetStatus}
                        className="text-gray-600"
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Desfazer
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : currentStatus === "rejected" ? (
                <Card className="border-2 border-red-200 bg-red-50">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-red-100 rounded-full">
                          <XCircle className="h-6 w-6 text-red-600" />
                        </div>
                        <div>
                          <p className="font-semibold text-red-800">Nota Rejeitada</p>
                          <p className="text-sm text-red-600">
                            {launchInfo?.rejectionReason || "Sem motivo informado"}
                          </p>
                        </div>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={handleResetStatus}
                        className="text-gray-600"
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reverter para Pendente
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : null}
            </div>

            {/* Modal de Rejeição */}
            {showRejectModal && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <Card className="w-full max-w-md mx-4">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2 text-red-800">
                      <XCircle className="h-5 w-5" />
                      Rejeitar Nota
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 mb-4">
                      Informe o motivo da rejeição desta nota fiscal.
                    </p>
                    <textarea
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      placeholder="Ex: Nota duplicada, valor incorreto, fornecedor não cadastrado..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                      rows={3}
                      autoFocus
                    />
                    <div className="flex gap-3 mt-4">
                      <Button 
                        variant="outline"
                        onClick={() => {
                          setShowRejectModal(false);
                          setRejectReason("");
                        }}
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                      <Button 
                        onClick={handleMarkAsRejected}
                        disabled={!rejectReason.trim()}
                        className="flex-1 bg-red-600 hover:bg-red-700"
                      >
                        Confirmar Rejeição
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <FileText className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Selecione uma nota para visualizar</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Componente para campo de dados copiável
function DataField({
  label,
  value,
  onCopy,
  copied,
  icon,
  highlight,
}: {
  label: string;
  value: string;
  onCopy: (text: string, field: string) => void;
  copied: string | null;
  icon?: React.ReactNode;
  highlight?: boolean;
}) {
  const fieldId = label.toLowerCase().replace(/\s/g, "-");
  const isCopied = copied === fieldId;

  return (
    <div>
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center gap-1">
        {icon}
        {label}
      </label>
      <div className="mt-1 flex items-center gap-2">
        <span
          className={cn(
            "flex-1 text-base",
            highlight ? "font-semibold text-blue-700" : "text-gray-900"
          )}
        >
          {value}
        </span>
        <button
          onClick={() => onCopy(value, fieldId)}
          className="p-1.5 hover:bg-gray-100 rounded transition-colors"
          title="Copiar"
        >
          {isCopied ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <Copy className="h-4 w-4 text-gray-400" />
          )}
        </button>
      </div>
    </div>
  );
}

// Componente para exibir valor monetário
function ValueCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number | null | undefined;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "p-4 rounded-lg",
        highlight ? "bg-green-50 border border-green-200" : "bg-gray-50"
      )}
    >
      <p className="text-sm text-gray-500">{label}</p>
      <p
        className={cn(
          "text-xl font-semibold mt-1",
          highlight ? "text-green-700" : "text-gray-900"
        )}
      >
        {formatCurrency(value)}
      </p>
    </div>
  );
}
