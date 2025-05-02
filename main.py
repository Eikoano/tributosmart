from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from fpdf import FPDF
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    tipo_atividade: str
    num_funcionarios: int

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
        {"nome": "Simples Nacional", "carga": 11.0, "justificativa": "Alíquota reduzida até R$ 4,8 milhões"},
        {"nome": "Lucro Presumido", "carga": 15.5, "justificativa": "Margem operacional alta"},
        {"nome": "Lucro Real", "carga": 18.2, "justificativa": "Indicado para margem baixa ou prejuízo"}
    ]

    return {
        "meta_carga_tributaria": empresa.meta_carga_tributaria,
        "estado_recomendado": melhor_opcao["estado"],
        "regime_recomendado": melhor_opcao["regime"],
        "carga_calculada": melhor_opcao["carga_efetiva"],
        "justificativa": melhor_opcao["justificativa"],
        "detalhamento_regimes": regimes,
        "simulacoes": resultados
    }

@app.post("/gerar-pdf")
async def gerar_pdf(empresa: EmpresaInput):
    resultados = [simular_estado(empresa, estado) for estado in empresa.estados_simulacao]
    melhor_opcao = min(resultados, key=lambda r: abs(r["carga_efetiva"] - empresa.meta_carga_tributaria))

    pdf = FPDF()
    pdf.add_page()

    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=33)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Relatório de Análise Tributária", ln=True, align="C")
    pdf.ln(20)

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Regime Recomendado: {melhor_opcao['regime']}", ln=True)
    pdf.cell(200, 10, txt=f"Carga Estimada: {melhor_opcao['carga_efetiva']}%", ln=True)
    pdf.cell(200, 10, txt=f"Estado Recomendado: {melhor_opcao['estado']}", ln=True)
    pdf.multi_cell(0, 10, txt=f"Justificativa: {melhor_opcao['justificativa']}")

    nome_arquivo = "relatorio_tributario.pdf"
    pdf.output(nome_arquivo)
    return FileResponse(nome_arquivo, media_type='application/pdf', filename=nome_arquivo)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
