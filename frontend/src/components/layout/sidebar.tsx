"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useNotesStore, useNfseStore } from "@/lib/store";
import {
  LayoutDashboard,
  FileText,
  Upload,
  FileCheck,
  Briefcase,
  Clock,
  CheckCircle,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  badge?: {
    pending?: number;
    launched?: number;
  };
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export function Sidebar() {
  const pathname = usePathname();
  
  // NF-e counts
  const { getPendingNotes, getLaunchedNotes, notes } = useNotesStore();
  const nfePending = getPendingNotes().length;
  const nfeLaunched = getLaunchedNotes().length;
  
  // NFS-e counts (pode ser expandido depois)
  const { nfseNotes } = useNfseStore();

  // Feature flag: esconder temporariamente a se??o de NFS-e
  const showNfse = false;
  
  const navigation: NavSection[] = [
    {
      title: "NF-e (Produtos)",
      items: [
        {
          name: "Painel do Gestor",
          href: "/",
          icon: LayoutDashboard,
          description: "Notas lançadas no ERP",
          badge: nfeLaunched > 0 ? { launched: nfeLaunched } : undefined,
        },
        {
          name: "Lançamento",
          href: "/lancamento",
          icon: FileCheck,
          description: "Conferir e lançar notas",
          badge: nfePending > 0 ? { pending: nfePending } : undefined,
        },
        {
          name: "Upload",
          href: "/upload",
          icon: Upload,
          description: "Enviar novas notas",
        },
      ],
    },
    // Se??o NFS-e oculta temporariamente; reative setando showNfse = true
    ...(showNfse
      ? [
          {
            title: "NFS-e (Serviços)",
            items: [
              {
                name: "Painel NFS-e",
                href: "/nfse",
                icon: Briefcase,
                description: "Vis?o geral dos serviços",
                badge: nfseNotes.length > 0 ? { launched: nfseNotes.length } : undefined,
              },
              {
                name: "Lançamento",
                href: "/nfse/lancamento",
                icon: FileCheck,
                description: "Conferir e lançar notas",
              },
              {
                name: "Upload",
                href: "/nfse/upload",
                icon: Upload,
                description: "Enviar novas notas",
              },
            ],
          },
        ]
      : []),
  ];
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <FileText className="h-8 w-8 text-blue-600" />
        <div className="ml-3">
          <h1 className="text-lg font-bold text-gray-900">NF Analyzer</h1>
          <p className="text-xs text-gray-500">Análise de Notas Fiscais</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-6 overflow-y-auto">
        {navigation.map((section) => (
          <div key={section.title}>
            <h3 className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {section.title}
            </h3>
            <div className="space-y-1">
              {section.items.map((item) => {
                const isActive = pathname === item.href || 
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center px-3 py-2.5 rounded-lg transition-colors group",
                      isActive
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-700 hover:bg-gray-100"
                    )}
                  >
                    <item.icon
                      className={cn(
                        "h-5 w-5 mr-3 flex-shrink-0",
                        isActive ? "text-blue-600" : "text-gray-400 group-hover:text-gray-600"
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <p className={cn(
                          "text-sm font-medium truncate",
                          isActive ? "text-blue-700" : "text-gray-900"
                        )}>
                          {item.name}
                        </p>
                        {/* Badge de status */}
                        {item.badge && (
                          <div className="flex items-center gap-1 ml-2">
                            {item.badge.pending !== undefined && item.badge.pending > 0 && (
                              <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">
                                <Clock className="h-3 w-3" />
                                {item.badge.pending}
                              </span>
                            )}
                            {item.badge.launched !== undefined && item.badge.launched > 0 && (
                              <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                                <CheckCircle className="h-3 w-3" />
                                {item.badge.launched}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 truncate">{item.description}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Resumo NF-e */}
      {notes.length > 0 && (
        <div className="px-4 pb-2">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-medium text-gray-600 mb-2">Status NF-e</p>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="bg-yellow-50 rounded px-2 py-1">
                <p className="text-lg font-bold text-yellow-700">{nfePending}</p>
                <p className="text-xs text-yellow-600">Pendentes</p>
              </div>
              <div className="bg-green-50 rounded px-2 py-1">
                <p className="text-lg font-bold text-green-700">{nfeLaunched}</p>
                <p className="text-xs text-green-600">Lançadas</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="bg-blue-50 rounded-lg p-4">
          <p className="text-xs font-medium text-blue-800">API Status</p>
          <div className="flex items-center mt-1">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <p className="ml-2 text-xs text-gray-600">Conectado</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
