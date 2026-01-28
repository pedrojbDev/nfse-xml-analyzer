# NF-e Analyzer - Frontend

Interface moderna para análise e lançamento de notas fiscais eletrônicas.

## Tecnologias

- **Next.js 14** - Framework React com App Router
- **TypeScript** - Tipagem estática
- **Tailwind CSS** - Estilização utilitária
- **shadcn/ui** - Componentes de UI
- **Zustand** - Gerenciamento de estado
- **TanStack Query** - Cache e fetch de dados

## Instalação

```bash
# Instalar dependências
npm install

# Copiar variáveis de ambiente
copy .env.example .env

# Iniciar em desenvolvimento
npm run dev
```

Acesse: http://localhost:3000

## Estrutura

```
frontend/
├── src/
│   ├── app/                    # Páginas (App Router)
│   │   ├── page.tsx            # Dashboard do Gestor
│   │   ├── upload/             # Upload de XMLs
│   │   └── lancamento/         # Conferência e Lançamento
│   ├── components/
│   │   ├── ui/                 # Componentes base (shadcn)
│   │   └── layout/             # Sidebar, Header
│   ├── lib/
│   │   ├── api.ts              # Chamadas à API
│   │   ├── store.ts            # Estado global (Zustand)
│   │   └── utils.ts            # Utilitários
│   └── types/                  # Tipos TypeScript
├── public/
├── package.json
└── tailwind.config.ts
```

## Páginas

### Painel do Gestor (/)

Visão geral com:
- KPIs (total de notas, valor, distribuição por risco)
- Classificação das notas (Medicamento, Material, Genérico)
- Lista resumida das notas recentes

### Upload (/upload)

- Drag & drop de arquivos XML
- Processamento em lote
- Feedback visual do status

### Lançamento (/lancamento)

Página principal para o operador com:
- Lista lateral das notas para lançar
- Dados essenciais para o ERP (com botão de copiar)
- Informações do fornecedor e destinatário
- Valores e impostos detalhados
- Pendências e motivos de revisão
- Próximos passos sugeridos

## API

O frontend se conecta à API FastAPI em `http://localhost:8000`.

Configure a URL no arquivo `.env`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Scripts

```bash
npm run dev      # Desenvolvimento
npm run build    # Build de produção
npm run start    # Iniciar produção
npm run lint     # Verificar código
```
