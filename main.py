from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from fpdf import FPDF
import uuid
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class EmpresaInput(BaseModel):
    cnae: str
    faturamento_anual: float
    folha_pagamento: float
    custos_operacionais: float
    estado: str
    municipio: str
    tipo_operacao: str
    percentual: float
    meta_carga_tributaria: float
    estados_simulacao: List[str]

def simular_estado(empresa: EmpresaInput, estado: str):
    if estado == "SP":
        carga = 13.5
    elif estado == "MG":
        carga = 14.2
    else:
        carga = 12.0

    regime = "Simples Nacional" if empresa.faturamento_anual <= 4800000 else "Lucro Presumido"
    justificativa = "Alíquota reduzida" if regime == "Simples Nacional" else "Vantagem pelo crédito de ICMS"

    return {
        "estado": estado,
        "regime": regime,
        "carga_efetiva": carga,
        "justificativa": justificativa
    }

@app.post("/analise-tributaria")
async def analisar_dados(empresa: EmpresaInput):
    resultados = [simular_estado(empresa, estado) for estado in empresa.estados_simulacao]
    melhor_opcao = min(resultados, key=lambda r: abs(r["carga_efetiva"] - empresa.meta_carga_tributaria))

    regimes = [
        {"nome": "Simples Nacional", "carga": 11.0, "justificativa": "Alíquota reduzida para empresas com faturamento até R$ 4,8 milhões."},
        {"nome": "Lucro Presumido", "carga": 15.5, "justificativa": "Boa opção com margem operacional alta e baixo custo."},
        {"nome": "Lucro Real", "carga": 18.2, "justificativa": "Mais vantajoso para empresas com prejuízo fiscal ou margens pequenas."}
    ]

    detalhes = [{"regime": r["nome"], "carga": r["carga"], "justificativa": r["justificativa"]} for r in regimes]

    return {
        "meta_carga_tributaria": empresa.meta_carga_tributaria,
        "estado_recomendado": melhor_opcao["estado"],
        "regime_recomendado": melhor_opcao["regime"],
        "carga_calculada": melhor_opcao["carga_efetiva"],
        "justificativa": melhor_opcao["justificativa"],
        "detalhamento_regimes": detalhes,
        "simulacoes": resultados
    }

@app.post("/gerar-pdf")
async def gerar_pdf(empresa: EmpresaInput):
    resultados = [simular_estado(empresa, estado) for estado in empresa.estados_simulacao]
    melhor_opcao = min(resultados, key=lambda r: abs(r["carga_efetiva"] - empresa.meta_carga_tributaria))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.set_text_color(0, 0, 80)
    pdf.cell(200, 10, "EIKON SOLUÇÕES - PLANEJAMENTO TRIBUTÁRIO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, f"CNAE: {empresa.cnae}", ln=True)
    pdf.cell(200, 10, f"Faturamento Anual: R$ {empresa.faturamento_anual:,.2f}", ln=True)
    pdf.cell(200, 10, f"Folha de Pagamento: R$ {empresa.folha_pagamento:,.2f}", ln=True)
    pdf.cell(200, 10, f"Custos Operacionais: R$ {empresa.custos_operacionais:,.2f}", ln=True)
    pdf.cell(200, 10, f"Estado Atual: {empresa.estado}", ln=True)
    pdf.cell(200, 10, f"Município: {empresa.municipio}", ln=True)
    pdf.cell(200, 10, f"Tipo de Operação: {empresa.tipo_operacao}", ln=True)
    pdf.cell(200, 10, f"% Vendas para outros estados: {empresa.percentual}%", ln=True)
    pdf.cell(200, 10, f"Meta de Carga: {empresa.meta_carga_tributaria}%", ln=True)
    pdf.ln(5)

    pdf.set_text_color(50, 90, 0)
    pdf.cell(200, 10, f"Recomendação: {melhor_opcao['regime']} em {melhor_opcao['estado']} ({melhor_opcao['carga_efetiva']}%)", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 10, f"Justificativa: {melhor_opcao['justificativa']}")
    pdf.ln(5)

    pdf.set_text_color(0, 0, 80)
    pdf.cell(200, 10, "Simulações por estado:", ln=True)
    pdf.set_text_color(0, 0, 0)
    for r in resultados:
        pdf.cell(200, 10, f"{r['estado']}: {r['regime']} - {r['carga_efetiva']}%", ln=True)

    pdf_path = f"static/relatorio_{uuid.uuid4().hex}.pdf"
    pdf.output(pdf_path)
    return FileResponse(path=pdf_path, filename="relatorio_tributario.pdf", media_type='application/pdf')

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
