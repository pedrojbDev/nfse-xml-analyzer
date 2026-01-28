/**
 * Configuração de Filiais IGH
 * 
 * Este arquivo contém o cadastro de todas as filiais e seus CNPJs.
 * A identificação da filial é feita pelo CNPJ do destinatário (dest) da NF-e.
 * 
 * Nota: Algumas unidades ainda não possuem CNPJ próprio e utilizam o da matriz.
 */

export interface Filial {
  codigo: number;         // Código RM
  nome: string;           // Nome fantasia
  cnpj: string;           // CNPJ (apenas dígitos)
  cnpjFormatado: string;  // CNPJ formatado
  municipio: string;
  uf: string;
  tipo: "matriz" | "filial" | "upa" | "aps" | "hospital" | "escritorio" | "clinica";
}

// CNPJ da Matriz (usado por várias unidades que ainda não têm CNPJ próprio)
export const CNPJ_MATRIZ = "11858570000133";

/**
 * Cadastro completo de filiais
 * Ordenado por código RM
 */
export const FILIAIS: Filial[] = [
  {
    codigo: 1,
    nome: "IGH MATRIZ",
    cnpj: "11858570000133",
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Salvador",
    uf: "BA",
    tipo: "matriz",
  },
  {
    codigo: 2,
    nome: "Hospital de Capim Grosso",
    cnpj: "11858570000303",
    cnpjFormatado: "11.858.570/0003-03",
    municipio: "Capim Grosso",
    uf: "BA",
    tipo: "hospital",
  },
  {
    codigo: 3,
    nome: "HMI - Hospital Materno-Infantil",
    cnpj: "11858570000214",
    cnpjFormatado: "11.858.570/0002-14",
    municipio: "Goiânia",
    uf: "GO",
    tipo: "hospital",
  },
  {
    codigo: 4,
    nome: "HEAPA - Hospital Estadual de Aparecida de Goiânia",
    cnpj: "11858570000486",
    cnpjFormatado: "11.858.570/0004-86",
    municipio: "Aparecida de Goiânia",
    uf: "GO",
    tipo: "hospital",
  },
  {
    codigo: 5,
    nome: "Unidade Goiânia 5",
    cnpj: "11858570000567",
    cnpjFormatado: "11.858.570/0005-67",
    municipio: "Goiânia",
    uf: "GO",
    tipo: "filial",
  },
  {
    codigo: 6,
    nome: "Hospital de Casimiro de Abreu",
    cnpj: "11858570000648",
    cnpjFormatado: "11.858.570/0006-48",
    municipio: "Casimiro de Abreu",
    uf: "RJ",
    tipo: "hospital",
  },
  {
    codigo: 7,
    nome: "UPA Cabula",
    cnpj: "11858570001024",
    cnpjFormatado: "11.858.570/0010-24",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 8,
    nome: "UPA Camaçari",
    cnpj: "11858570000729",
    cnpjFormatado: "11.858.570/0007-29",
    municipio: "Camaçari",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 9,
    nome: "Hospital de Porto Seguro",
    cnpj: "11858570000800",
    cnpjFormatado: "11.858.570/0008-00",
    municipio: "Porto Seguro",
    uf: "BA",
    tipo: "hospital",
  },
  {
    codigo: 10,
    nome: "HRJL - Hospital Regional Justino Luz",
    cnpj: "11858570000990",
    cnpjFormatado: "11.858.570/0009-90",
    municipio: "Picos",
    uf: "PI",
    tipo: "hospital",
  },
  {
    codigo: 11,
    nome: "Cachoeiras de Macacu",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Cachoeiras de Macacu",
    uf: "RJ",
    tipo: "filial",
  },
  {
    codigo: 12,
    nome: "UPA Caxias do Sul",
    cnpj: "11858570001105",
    cnpjFormatado: "11.858.570/0011-05",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 13,
    nome: "HIMABA",
    cnpj: "11858570001296",
    cnpjFormatado: "11.858.570/0012-96",
    municipio: "Vila Velha",
    uf: "ES",
    tipo: "hospital",
  },
  {
    codigo: 14,
    nome: "MJMMN - Maternidade José Maria de Magalhães Neto",
    cnpj: "11858570001377",
    cnpjFormatado: "11.858.570/0013-77",
    municipio: "Salvador",
    uf: "BA",
    tipo: "hospital",
  },
  {
    codigo: 15,
    nome: "Contagem",
    cnpj: "11858570001458",
    cnpjFormatado: "11.858.570/0014-58",
    municipio: "Contagem",
    uf: "MG",
    tipo: "filial",
  },
  {
    codigo: 16,
    nome: "Hospital de Mairi",
    cnpj: "11858570001610",
    cnpjFormatado: "11.858.570/0016-10",
    municipio: "Mairi",
    uf: "BA",
    tipo: "hospital",
  },
  {
    codigo: 17,
    nome: "Barra",
    cnpj: "11858570001539",
    cnpjFormatado: "11.858.570/0015-39",
    municipio: "Barra",
    uf: "BA",
    tipo: "filial",
  },
  {
    codigo: 18,
    nome: "UPA Boca do Rio",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 19,
    nome: "UPA Pernambués",
    cnpj: "11858570001881",
    cnpjFormatado: "11.858.570/0018-81",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 20,
    nome: "Hospital Pituba",
    cnpj: "11858570002268",
    cnpjFormatado: "11.858.570/0022-68",
    municipio: "Salvador",
    uf: "BA",
    tipo: "hospital",
  },
  {
    codigo: 22,
    nome: "UPA São Cristóvão",
    cnpj: "11858570002853",
    cnpjFormatado: "11.858.570/0028-53",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 23,
    nome: "APS Camaçari",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Camaçari",
    uf: "BA",
    tipo: "aps",
  },
  {
    codigo: 24,
    nome: "Hospital Santa Maria",
    cnpj: "11858570001962",
    cnpjFormatado: "11.858.570/0019-62",
    municipio: "Goiânia",
    uf: "GO",
    tipo: "hospital",
  },
  {
    codigo: 25,
    nome: "APS Vitória da Conquista",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Vitória da Conquista",
    uf: "BA",
    tipo: "aps",
  },
  {
    codigo: 26,
    nome: "Escritório Regional de Goiás",
    cnpj: "11858570001709",
    cnpjFormatado: "11.858.570/0017-09",
    municipio: "Goiânia",
    uf: "GO",
    tipo: "escritorio",
  },
  {
    codigo: 28,
    nome: "APS Natal",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Natal",
    uf: "RN",
    tipo: "aps",
  },
  {
    codigo: 32,
    nome: "UPA Paripe",
    cnpj: "11858570002772",
    cnpjFormatado: "11.858.570/0027-72",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 33,
    nome: "UPA Pirajá",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Salvador",
    uf: "BA",
    tipo: "upa",
  },
  {
    codigo: 34,
    nome: "APS Aracaju",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Aracaju",
    uf: "SE",
    tipo: "aps",
  },
  {
    codigo: 35,
    nome: "Hospital de Anápolis",
    cnpj: "11858570000133", // Usa CNPJ da matriz
    cnpjFormatado: "11.858.570/0001-33",
    municipio: "Anápolis",
    uf: "GO",
    tipo: "hospital",
  },
  {
    codigo: 36,
    nome: "Hospital Regional de Eunápolis",
    cnpj: "11858570002187",
    cnpjFormatado: "11.858.570/0021-87",
    municipio: "Eunápolis",
    uf: "BA",
    tipo: "hospital",
  },
  {
    codigo: 37,
    nome: "Nefrologia",
    cnpj: "11858570002004",
    cnpjFormatado: "11.858.570/0020-04",
    municipio: "Salvador",
    uf: "BA",
    tipo: "clinica",
  },
  {
    codigo: 38,
    nome: "Maternidade Maria de Lourdes Santana Nogueira",
    cnpj: "11858570002349",
    cnpjFormatado: "11.858.570/0023-49",
    municipio: "Aracaju",
    uf: "SE",
    tipo: "hospital",
  },
  {
    codigo: 39,
    nome: "IGH ADM",
    cnpj: "11858570002691",
    cnpjFormatado: "11.858.570/0026-91",
    municipio: "Salvador",
    uf: "BA",
    tipo: "escritorio",
  },
  {
    codigo: 40,
    nome: "Clínica IGH Healthcare",
    cnpj: "11858570002500",
    cnpjFormatado: "11.858.570/0025-00",
    municipio: "Salvador",
    uf: "BA",
    tipo: "clinica",
  },
];

/**
 * Mapa de CNPJ -> Filial para busca rápida
 * Nota: Filiais que usam CNPJ da matriz são mapeadas para a matriz
 */
const cnpjToFilialMap: Map<string, Filial> = new Map();

// Inicializa o mapa - CNPJs únicos apontam para suas filiais
// CNPJs duplicados (matriz) apontam para a matriz
FILIAIS.forEach((filial) => {
  // Se o CNPJ é único ou é a matriz, adiciona ao mapa
  if (filial.cnpj !== CNPJ_MATRIZ || filial.codigo === 1) {
    cnpjToFilialMap.set(filial.cnpj, filial);
  }
});

/**
 * Remove formatação do CNPJ (pontos, barras, traços)
 */
export function normalizeCnpj(cnpj: string | null | undefined): string {
  if (!cnpj) return "";
  return cnpj.replace(/\D/g, "");
}

/**
 * Formata CNPJ para exibição
 */
export function formatCnpj(cnpj: string | null | undefined): string {
  const digits = normalizeCnpj(cnpj);
  if (digits.length !== 14) return cnpj || "";
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12, 14)}`;
}

/**
 * Busca filial pelo CNPJ do destinatário da NF-e
 * 
 * @param cnpjDest CNPJ do destinatário (campo dest.doc da NF-e)
 * @returns Filial encontrada ou null se não for uma filial IGH
 */
export function getFilialByCnpj(cnpjDest: string | null | undefined): Filial | null {
  const cnpjNormalizado = normalizeCnpj(cnpjDest);
  if (!cnpjNormalizado) return null;
  
  return cnpjToFilialMap.get(cnpjNormalizado) || null;
}

/**
 * Verifica se um CNPJ pertence ao grupo IGH
 */
export function isIghCnpj(cnpj: string | null | undefined): boolean {
  const normalizado = normalizeCnpj(cnpj);
  if (!normalizado) return false;
  
  // Todos os CNPJs IGH começam com 11858570
  return normalizado.startsWith("11858570");
}

/**
 * Retorna a filial matriz
 */
export function getMatriz(): Filial {
  return FILIAIS.find((f) => f.codigo === 1)!;
}

/**
 * Lista de UFs onde a IGH tem unidades
 */
export function getUfsComUnidades(): string[] {
  const ufs = new Set<string>();
  FILIAIS.forEach((f) => ufs.add(f.uf));
  return Array.from(ufs).sort();
}

/**
 * Filtra filiais por UF
 */
export function getFilialPorUf(uf: string): Filial[] {
  return FILIAIS.filter((f) => f.uf === uf);
}

/**
 * Retorna cor do badge baseado no tipo da filial
 */
export function getFilialTypeColor(tipo: Filial["tipo"]): string {
  const colors: Record<Filial["tipo"], string> = {
    matriz: "bg-blue-100 text-blue-800 border-blue-200",
    hospital: "bg-green-100 text-green-800 border-green-200",
    upa: "bg-orange-100 text-orange-800 border-orange-200",
    aps: "bg-purple-100 text-purple-800 border-purple-200",
    filial: "bg-gray-100 text-gray-800 border-gray-200",
    escritorio: "bg-cyan-100 text-cyan-800 border-cyan-200",
    clinica: "bg-pink-100 text-pink-800 border-pink-200",
  };
  return colors[tipo] || "bg-gray-100 text-gray-600";
}

/**
 * Traduz tipo de filial para português
 */
export function translateFilialType(tipo: Filial["tipo"]): string {
  const labels: Record<Filial["tipo"], string> = {
    matriz: "Matriz",
    hospital: "Hospital",
    upa: "UPA",
    aps: "APS",
    filial: "Filial",
    escritorio: "Escritório",
    clinica: "Clínica",
  };
  return labels[tipo] || tipo;
}
