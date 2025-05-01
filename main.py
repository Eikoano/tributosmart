from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Configuração de diretórios
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Modelo de entrada
class EmpresaInput(BaseModel):
    cnae: str
    faturamento_anual: float
    folha_pagamento: float
    custos_operacionais: float
    estado: str
    municipio: str
    tipo_operacao: str
    percentual_vendas_outros_estados: float

# Rota da API de análise
@app.post("/analise-tributaria")
def analisar_dados(empresa: EmpresaInput):
    fator_r = empresa.folha_pagamento / empresa.faturamento_anual
    simples_aliquota = 0.155 if fator_r < 0.28 else 0.11
    simples_total = round(empresa.faturamento_anual * simples_aliquota, 2)

    pres_base = empresa.faturamento_anual * 0.32
    irpj = pres_base * 0.15
    adicional_irpj = max(0, ((pres_base / 4) - 60000) * 0.10)
    csll = pres_base * 0.09
    pis = empresa.faturamento_anual * 0.0065
    cofins = empresa.faturamento_anual * 0.03
    iss = empresa.faturamento_anual * 0.02
    presumido_total = round(irpj + adicional_irpj + csll + pis + cofins + iss, 2)

    lucro = empresa.faturamento_anual - empresa.folha_pagamento - empresa.custos_operacionais
    real_irpj = lucro * 0.15
    adicional_real_irpj = max(0, ((lucro / 4) - 60000) * 0.10)
    real_csll = lucro * 0.09
    real_pis = empresa.faturamento_anual * 0.0165
    real_cofins = empresa.faturamento_anual * 0.076
    real_iss = empresa.faturamento_anual * 0.02
    real_total = round(real_irpj + adicional_real_irpj + real_csll + real_pis + real_cofins + real_iss, 2)

    regime_ideal = min([
        ("Simples Nacional", simples_total),
        ("Lucro Presumido", presumido_total),
        ("Lucro Real", real_total)
    ], key=lambda x: x[1])
    economia = max([simples_total, presumido_total, real_total]) - regime_ideal[1]

    return {
        "simples_nacional": {
            "aliquota_efetiva": simples_aliquota * 100,
            "imposto_total": simples_total
        },
        "lucro_presumido": {
            "aliquota_efetiva": round(presumido_total / empresa.faturamento_anual * 100, 2),
            "imposto_total": presumido_total
        },
        "lucro_real": {
            "aliquota_efetiva": round(real_total / empresa.faturamento_anual * 100, 2),
            "imposto_total": real_total
        },
        "regime_recomendado": regime_ideal[0],
        "economia_anual": round(economia, 2)
    }

# Rota da página web
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
