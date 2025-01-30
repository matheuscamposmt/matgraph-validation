import streamlit as st
import json
import boto3
import toml
from pydantic import ValidationError
from typing import List, Dict
from pathlib import Path

# Load environment variables from .streamlit/secrets.toml
secrets = toml.load(".streamlit/secrets.toml")
AWS_ACCESS_KEY = secrets["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = secrets["AWS_SECRET_KEY"]
S3_BUCKET = "matricula-extractor"

# Initialize S3 client
@st.cache_resource
def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

s3_client = get_s3_client()

# Importando os modelos do JSON Schema
from pydantic import BaseModel

class Pessoa(BaseModel):
    nome: str
    documento: str
    tipo_documento: str

class Valor(BaseModel):
    valor: float
    moeda: str

class Registro(BaseModel):
    tipo: str
    valor: Valor
    data: str
    objeto: str
    pct: float
    alienantes: List[Pessoa]
    adquirentes: List[Pessoa]

class Imovel(BaseModel):
    proprietarios: List[Pessoa]
    area: float
    area_unidade: str

class Matricula(BaseModel):
    registros: List[Registro]
    bem: Imovel

# Função para carregar progresso do S3
def load_progress():
    try:
        if st.session_state.get("progress"):
            return st.session_state.progress
        response = s3_client.get_object(Bucket=S3_BUCKET, Key="validation_progress.json")
        st.session_state.progress = json.load(response["Body"])
        return st.session_state.progress
    except s3_client.exceptions.NoSuchKey:
        return {}

def save_progress(progress):
    s3_client.put_object(Bucket=S3_BUCKET, Key="validation_progress.json", Body=json.dumps(progress, indent=4))


# Interface do Streamlit
st.title("Validação Manual de Registros")

uploaded_files = st.file_uploader("Carregar JSONs para validação", type=["json"], accept_multiple_files=True)

progress = load_progress()
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        json_data = json.load(uploaded_file)
        try:
            matricula = Matricula(**json_data)
        except ValidationError as e:
            st.error(f"Arquivo {file_name} inválido. Verifique o formato.")
            st.text(e)
            continue
        
        if file_name not in progress:
            progress[file_name] = {}
        
        with st.expander(f"Arquivo: {file_name}"):
            # Paginação dos registros
            num_registros = len(matricula.registros)
            if num_registros == 0:
                st.error("Nenhum registro encontrado.")
                continue
            # Paginação dos registros
            registros_por_pagina = 3
            num_paginas = (num_registros + registros_por_pagina - 1) // registros_por_pagina
            
            if f"pagina_idx_{file_name}" not in st.session_state:
                st.session_state[f"pagina_idx_{file_name}"] = 0
            pagina_idx = st.session_state.get(f"pagina_idx_{file_name}", 0)
            cont = st.container()
            if num_paginas > 1:
                col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                with col1:
                    if st.button("Página Anterior", key=f"prev_page_{file_name}"):
                        pagina_idx = max(pagina_idx - 1, 0)
                with col2:
                    st.write(f"Página {pagina_idx + 1} de {num_paginas}")
                with col3:
                    if st.button("Próxima Página", key=f"next_page_{file_name}"):
                        pagina_idx = min(pagina_idx + 1, num_paginas - 1)
                with col4:
                    if st.button("Finalizar Arquivo", key=f"finalizar_{file_name}"):
                        progress[file_name]["finalizado"] = True
                        st.success(f"Arquivo {file_name} finalizado!")
            else:
                pagina_idx = 0

            inicio = pagina_idx * registros_por_pagina
            fim = min(inicio + registros_por_pagina, num_registros)
            
            with cont:
                for registro_idx in range(inicio, fim):
                    registro = matricula.registros[registro_idx]
                    st.subheader(f"Registro {registro_idx + 1}")
                    st.json(registro.model_dump(mode='json'))
                    
                    if str(registro_idx) not in progress[file_name]:
                        progress[file_name][str(registro_idx)] = {}

                    # Checkboxes para validação dos campos
                    progress[file_name][str(registro_idx)]["tipo"] = st.checkbox(f"Tipo de registro correto?", key=f"tipo_{file_name}_{registro_idx}", value=progress[file_name][str(registro_idx)].get("tipo", False))
                    progress[file_name][str(registro_idx)]["valor"] = st.checkbox(f"Valor correto?", key=f"valor_{file_name}_{registro_idx}", value=progress[file_name][str(registro_idx)].get("valor", False))
                    
                    # Organização dos documentos das pessoas
                    for person_idx, alienante in enumerate(registro.alienantes):
                        progress[file_name][str(registro_idx)][f"doc_alienante_{person_idx}"] = st.checkbox(f"{alienante.nome} - {alienante.documento} (Alienante)", key=f"doc_alienante_{file_name}_{registro_idx}_{person_idx}", value=progress[file_name][str(registro_idx)].get(f"doc_alienante_{person_idx}", False))
                    for person_idx, adquirente in enumerate(registro.adquirentes):
                        progress[file_name][str(registro_idx)][f"doc_adquirente_{person_idx}"] = st.checkbox(f"{adquirente.nome} - {adquirente.documento} (Adquirente)", key=f"doc_adquirente_{file_name}_{registro_idx}_{person_idx}", value=progress[file_name][str(registro_idx)].get(f"doc_adquirente_{person_idx}", False))
                    
                    st.write("---")
    
    # Menu lateral para gerenciar progresso
    with st.sidebar:
        st.subheader("Gerenciamento de Progresso")
        if st.button("Salvar Progresso"):
            save_progress(progress)
            st.success("Progresso salvo com sucesso no S3!")
