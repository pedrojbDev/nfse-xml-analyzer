# NF-e Analyzer

Sistema completo para análise automatizada de Notas Fiscais Eletrônicas (NF-e).

## Visão Geral

Este sistema:

1. **Recebe** NF-e em formato XML (individual ou ZIP)
2. **Extrai** campos principais (cabeçalho, emitente, destinatário, totais, itens)
3. **Normaliza/Classifica** itens e documentos (MEDICAMENTO, MATERIAL_HOSPITALAR, GENERICO)
4. **Gera explicações** auditáveis para cada decisão
5. **Entrega** dados estruturados para integração com ERP

## Estrutura do Projeto

```
api_nf/
├── app/                        # Backend (FastAPI)
│   ├── api/endpoints/          # Endpoints da API
│   ├── core/                   # Configurações e exceções
│   ├── schemas/                # Modelos Pydantic
│   ├── services/               # Lógica de negócio
│   └── utils/                  # Utilitários
├── frontend/                   # Frontend (Next.js)
│   ├── src/app/                # Páginas
│   ├── src/components/         # Componentes UI
│   └── src/lib/                # Utilitários e API
├── data/                       # Logs de auditoria
├── requirements.txt            # Dependências Python
└── .env.example                # Template de ambiente
```

## Instalação

### Backend (API)

```bash
# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Copiar variáveis de ambiente
copy .env.example .env

# Iniciar API
uvicorn app.main:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd frontend

# Instalar dependências
npm install

# Copiar variáveis de ambiente
copy .env.example .env

# Iniciar em desenvolvimento
npm run dev
```

## Acessos

- **API**: http://localhost:8000
- **Documentação API**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

## Funcionalidades

### Painel do Gestor

- Visão geral com KPIs (total de notas, valor, distribuição por risco)
- Classificação automática das notas
- Lista de notas com status de risco

### Página de Lançamento

- Dados completos para lançamento no ERP
- Botões de copiar para cada campo
- Informações do fornecedor e destinatário
- Valores e impostos detalhados
- Pendências e motivos de revisão
- Próximos passos sugeridos

### Upload

- Drag & drop de arquivos XML
- Processamento em lote
- Feedback visual do status

## Classificação

O sistema classifica itens com base em:

| Critério | Classificação |
|----------|---------------|
| NCM capítulo 30 | Medicamento |
| NCM capítulo 90 | Material Hospitalar |
| Keywords na descrição | Material Hospitalar |
| Sem evidências | Genérico |

## Níveis de Risco

| Nível | Descrição |
|-------|-----------|
| **Alto** | Dados críticos ausentes ou divergências significativas |
| **Médio** | Pequenas inconsistências ou dados faltantes não-críticos |
| **Baixo** | Dados completos, apenas validação final necessária |

## Tecnologias

### Backend
- Python 3.11+
- FastAPI
- Pydantic
- lxml

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS
- Zustand
- TanStack Query

## Licença

Projeto interno - uso restrito.
