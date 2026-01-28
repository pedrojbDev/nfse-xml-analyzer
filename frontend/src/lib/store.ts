"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { ProcessedNote, NFeExtractResponse, NoteLaunchStatus, NoteFilialInfo } from "@/types/nfe";
import { ProcessedNfse, NfseExtractResponse } from "@/types/nfse";
import { getFilialByCnpj, getMatriz, Filial } from "@/lib/filiais";

// ============================================================================
// Helper: Identifica a filial pelo CNPJ do destinatário
// ============================================================================

function identifyFilial(destCnpj: string | null | undefined): NoteFilialInfo | null {
  const filial = getFilialByCnpj(destCnpj);
  
  if (!filial) {
    // Se não encontrou pelo CNPJ, pode não ser uma nota do grupo IGH
    return null;
  }
  
  return {
    codigo: filial.codigo,
    nome: filial.nome,
    cnpj: filial.cnpj,
    cnpjFormatado: filial.cnpjFormatado,
    municipio: filial.municipio,
    uf: filial.uf,
    tipo: filial.tipo,
  };
}

// ============================================================================
// Store de NF-e
// ============================================================================

interface NotesStore {
  notes: ProcessedNote[];
  selectedNoteId: string | null;
  
  // Actions básicas
  addNote: (filename: string, data: NFeExtractResponse) => void;
  addNotes: (notes: { filename: string; data: NFeExtractResponse }[]) => void;
  removeNote: (id: string) => void;
  clearNotes: () => void;
  selectNote: (id: string | null) => void;
  getSelectedNote: () => ProcessedNote | null;
  
  // Actions de lançamento
  markAsLaunched: (id: string, operatorName?: string, notes?: string) => void;
  markAsRejected: (id: string, reason: string, operatorName?: string) => void;
  resetLaunchStatus: (id: string) => void;
  
  // Getters filtrados
  getPendingNotes: () => ProcessedNote[];
  getLaunchedNotes: () => ProcessedNote[];
  getRejectedNotes: () => ProcessedNote[];
  
  // Getters por filial
  getNotesByFilial: (codigoFilial: number) => ProcessedNote[];
  getFilialStats: () => Map<number, { filial: NoteFilialInfo; count: number; valor: number }>;
}

// Gera ID único
const generateId = () => Math.random().toString(36).substring(2, 15);

export const useNotesStore = create<NotesStore>()(
  persist(
    (set, get) => ({
      notes: [],
      selectedNoteId: null,

      addNote: (filename, data) => {
        // Identifica a filial pelo CNPJ do destinatário
        const filial = identifyFilial(data.dest?.doc);
        
        const note: ProcessedNote = {
          id: generateId(),
          filename,
          data,
          processedAt: new Date(),
          launchInfo: {
            status: "pending",
          },
          filial,
        };
        set((state) => ({ notes: [...state.notes, note] }));
      },

      addNotes: (notesToAdd) => {
        const newNotes: ProcessedNote[] = notesToAdd.map(({ filename, data }) => {
          // Identifica a filial pelo CNPJ do destinatário
          const filial = identifyFilial(data.dest?.doc);
          
          return {
            id: generateId(),
            filename,
            data,
            processedAt: new Date(),
            launchInfo: {
              status: "pending",
            },
            filial,
          };
        });
        set((state) => ({ notes: [...state.notes, ...newNotes] }));
      },

      removeNote: (id) => {
        set((state) => ({
          notes: state.notes.filter((n) => n.id !== id),
          selectedNoteId: state.selectedNoteId === id ? null : state.selectedNoteId,
        }));
      },

      clearNotes: () => {
        set({ notes: [], selectedNoteId: null });
      },

      selectNote: (id) => {
        set({ selectedNoteId: id });
      },

      getSelectedNote: () => {
        const { notes, selectedNoteId } = get();
        return notes.find((n) => n.id === selectedNoteId) || null;
      },

      // === Ações de Lançamento ===
      
      markAsLaunched: (id, operatorName, notes) => {
        set((state) => ({
          notes: state.notes.map((n) =>
            n.id === id
              ? {
                  ...n,
                  launchInfo: {
                    ...n.launchInfo,
                    status: "launched" as NoteLaunchStatus,
                    launchedAt: new Date(),
                    launchedBy: operatorName,
                    notes: notes,
                  },
                }
              : n
          ),
        }));
      },

      markAsRejected: (id, reason, operatorName) => {
        set((state) => ({
          notes: state.notes.map((n) =>
            n.id === id
              ? {
                  ...n,
                  launchInfo: {
                    ...n.launchInfo,
                    status: "rejected" as NoteLaunchStatus,
                    rejectedAt: new Date(),
                    rejectedBy: operatorName,
                    rejectionReason: reason,
                  },
                }
              : n
          ),
        }));
      },

      resetLaunchStatus: (id) => {
        set((state) => ({
          notes: state.notes.map((n) =>
            n.id === id
              ? {
                  ...n,
                  launchInfo: {
                    status: "pending" as NoteLaunchStatus,
                  },
                }
              : n
          ),
        }));
      },

      // === Getters Filtrados ===
      
      getPendingNotes: () => {
        const { notes } = get();
        return notes.filter((n) => n.launchInfo?.status === "pending" || !n.launchInfo);
      },

      getLaunchedNotes: () => {
        const { notes } = get();
        return notes.filter((n) => n.launchInfo?.status === "launched");
      },

      getRejectedNotes: () => {
        const { notes } = get();
        return notes.filter((n) => n.launchInfo?.status === "rejected");
      },

      // === Getters por Filial ===
      
      getNotesByFilial: (codigoFilial) => {
        const { notes } = get();
        return notes.filter((n) => n.filial?.codigo === codigoFilial);
      },

      getFilialStats: () => {
        const { notes } = get();
        const stats = new Map<number, { filial: NoteFilialInfo; count: number; valor: number }>();
        
        notes.forEach((note) => {
          if (!note.filial) return;
          
          const codigo = note.filial.codigo;
          const valor = note.data.totals?.vNF || 0;
          
          if (stats.has(codigo)) {
            const current = stats.get(codigo)!;
            current.count += 1;
            current.valor += valor;
          } else {
            stats.set(codigo, {
              filial: note.filial,
              count: 1,
              valor,
            });
          }
        });
        
        return stats;
      },
    }),
    {
      name: "nfe-notes-storage",
      partialize: (state) => ({ notes: state.notes }),
    }
  )
);

// ============================================================================
// Store de NFS-e
// ============================================================================

interface NfseStore {
  nfseNotes: ProcessedNfse[];
  selectedNfseId: string | null;
  
  // Actions
  addNfse: (filename: string, data: NfseExtractResponse) => void;
  addNfseNotes: (notes: { filename: string; data: NfseExtractResponse }[]) => void;
  removeNfse: (id: string) => void;
  clearNfseNotes: () => void;
  selectNfse: (id: string | null) => void;
  getSelectedNfse: () => ProcessedNfse | null;
}

export const useNfseStore = create<NfseStore>()(
  persist(
    (set, get) => ({
      nfseNotes: [],
      selectedNfseId: null,

      addNfse: (filename, data) => {
        const note: ProcessedNfse = {
          id: generateId(),
          filename,
          data,
          processedAt: new Date(),
        };
        set((state) => ({ nfseNotes: [...state.nfseNotes, note] }));
      },

      addNfseNotes: (notesToAdd) => {
        const newNotes: ProcessedNfse[] = notesToAdd.map(({ filename, data }) => ({
          id: generateId(),
          filename,
          data,
          processedAt: new Date(),
        }));
        set((state) => ({ nfseNotes: [...state.nfseNotes, ...newNotes] }));
      },

      removeNfse: (id) => {
        set((state) => ({
          nfseNotes: state.nfseNotes.filter((n) => n.id !== id),
          selectedNfseId: state.selectedNfseId === id ? null : state.selectedNfseId,
        }));
      },

      clearNfseNotes: () => {
        set({ nfseNotes: [], selectedNfseId: null });
      },

      selectNfse: (id) => {
        set({ selectedNfseId: id });
      },

      getSelectedNfse: () => {
        const { nfseNotes, selectedNfseId } = get();
        return nfseNotes.find((n) => n.id === selectedNfseId) || null;
      },
    }),
    {
      name: "nfse-notes-storage",
      partialize: (state) => ({ nfseNotes: state.nfseNotes }),
    }
  )
);
