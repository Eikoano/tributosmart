from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from fpdf import FPDF
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
        {"nome": "Simples Nacional", "carga": 11.0, "justificativa": "Reduzida para micro e pequenas empresas."},
        {"nome": "Lucro Presumido", "carga": 15.5, "justificativa": "Base fixa e boa margem para serviços."},
        {"nome": "Lucro Real", "carga": 18.2, "justificativa": "Mais indicado quando há prejuízo fiscal ou margens baixas."}
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

    # Caminho absoluto para a logo
    logo_path = os.path.join(os.getcwd(), "static", "logo.png")
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=8, w=30)
        except Exception as e:
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, f"[ERRO ao carregar logo: {e}]", ln=True)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, "[Logo não encontrada]", ln=True)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(80)
    pdf.cell(30, 10, "Relatório de Análise Tributária", ln=1, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"CNAE: {empresa.cnae}", ln=True)
    pdf.cell(0, 10, f"Tipo de Atividade: {empresa.tipo_atividade.capitalize()}", ln=True)
    pdf.cell(0, 10, f"Faturamento: R$ {empresa.faturamento_anual:,.2f}", ln=True)
    pdf.cell(0, 10, f"Funcionários: {empresa.num_funcionarios}", ln=True)
    pdf.cell(0, 10, f"Meta de Carga: {empresa.meta_carga_tributaria}%", ln=True)
    pdf.cell(0, 10, f"Regime Recomendado: {melhor_opcao['regime']}", ln=True)
    pdf.multi_cell(0, 10, f"Justificativa: {melhor_opcao['justificativa']}")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Simulações por Estado:", ln=True)
    pdf.set_font("Arial", size=12)
    for r in resultados:
        pdf.cell(0, 10, f"{r['estado']}: {r['carga_efetiva']}% - {r['regime']}", ln=True)

    output_path = "relatorio_tributario.pdf"
    pdf.output(output_path)
    return FileResponse(output_path, media_type='application/pdf', filename=output_path)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
