from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class EmpresaInput(BaseModel):
    faturamento_anual: float
    folha_pagamento: float
    custos_operacionais: float
    meta_carga_tributaria: float
    estados_simulacao: List[str]

def simular_carga(faturamento, folha, custos, estado):
    fator_r = folha / faturamento
    simples_aliquota = 0.155 if fator_r < 0.28 else 0.11
    simples_total = faturamento * simples_aliquota

    pres_base = faturamento * 0.32
    irpj = pres_base * 0.15
    adicional_irpj = max(0, ((pres_base / 4) - 60000) * 0.10)
    csll = pres_base * 0.09
    pis = faturamento * 0.0065
    cofins = faturamento * 0.03
    iss = faturamento * 0.02
    presumido_total = irpj + adicional_irpj + csll + pis + cofins + iss

    lucro = faturamento - folha - custos
    real_irpj = lucro * 0.15
    adicional_real_irpj = max(0, ((lucro / 4) - 60000) * 0.10)
    real_csll = lucro * 0.09
    real_pis = faturamento * 0.0165
    real_cofins = faturamento * 0.076
    real_iss = faturamento * 0.02
    real_total = real_irpj + adicional_real_irpj + real_csll + real_pis + real_cofins + real_iss

    regimes = [
        ("Simples Nacional", simples_total),
        ("Lucro Presumido", presumido_total),
        ("Lucro Real", real_total),
    ]

    regime_ideal = min(regimes, key=lambda x: x[1])
    carga_efetiva = regime_ideal[1] / faturamento * 100

    explicacao = f"No estado {estado}, o regime '{regime_ideal[0]}' gera carga de {carga_efetiva:.2f}%."

    return {
        "estado": estado,
        "regime": regime_ideal[0],
        "carga_efetiva": round(carga_efetiva, 2),
        "justificativa": explicacao
    }

@app.post("/analise-tributaria")
def analisar_dados(empresa: EmpresaInput):
    resultados = []

    for estado in empresa.estados_simulacao:
        resultado = simular_carga(
            empresa.faturamento_anual,
            empresa.folha_pagamento,
            empresa.custos_operacionais,
            estado.upper()
        )
        resultados.append(resultado)

    melhor_opcao = min(resultados, key=lambda r: abs(r["carga_efetiva"] - empresa.meta_carga_tributaria))

    return {
        "meta_carga_tributaria": empresa.meta_carga_tributaria,
        "estado_recomendado": melhor_opcao["estado"],
        "regime_recomendado": melhor_opcao["regime"],
        "carga_calculada": melhor_opcao["carga_efetiva"],
        "justificativa": melhor_opcao["justificativa"]
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
