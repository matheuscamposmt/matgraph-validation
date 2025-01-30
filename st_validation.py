import streamlit as st
import json
from pydantic import ValidationError
from typing import List
from pathlib import Path

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

# Função para carregar progresso
SAVE_FILE = "validation_progress.json"
def load_progress():
    if Path(SAVE_FILE).exists():
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with open(SAVE_FILE, "w") as f:
        json.dump(progress, f, indent=4)

# Carregando progresso salvo
if "progress" not in st.session_state:
    st.session_state.progress = load_progress()

progress = st.session_state.progress

# Interface do Streamlit
st.title("Validação Manual de Registros")

uploaded_files = st.file_uploader("Carregar JSONs para validação", type=["json"], accept_multiple_files=True)
st.write("## Progresso de validação:")
# Exibir progresso carregado mesmo sem arquivos carregados
for file_name, file_progress in progress.items():
    with st.expander(f"Arquivo: {file_name}"):
        for registro_idx, registro_progress in file_progress.items():
            st.subheader(f"Registro {int(registro_idx) + 1}")
            for key, value in registro_progress.items():
                st.checkbox(key, value=value, disabled=True, key=f"{file_name}_{registro_idx}_{key}")
            st.write("---")



if uploaded_files:
    st.write("## Arquivos carregados:")
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        json_data = json.load(uploaded_file)
        try:
            matricula = Matricula(**json_data)
            st.success(f"Arquivo {file_name} válido! Exibindo os registros para validação.")
        except ValidationError as e:
            st.error(f"Arquivo {file_name} inválido. Verifique o formato.")
            st.text(e)
            continue
        
        if file_name not in progress:
            progress[file_name] = {}
        
        with st.expander(f"Arquivo: {file_name}"):
            # Paginação dos registros
            num_registros = len(matricula.registros)
            registro_idx = st.number_input(f"Selecionar Registro", min_value=1, max_value=num_registros, value=1, key=f"registro_idx_{file_name}") - 1
            
            registro = matricula.registros[registro_idx]
            st.subheader(f"Registro {registro_idx + 1}")
            st.json(registro.model_dump(mode='json'))
            
            if str(registro_idx) not in progress[file_name]:
                progress[file_name][str(registro_idx)] = {}
            if st.button(f"Marcar todos os campos como corretos - Registro {registro_idx + 1}", key=f"mark_all_{file_name}_{registro_idx}"):
                progress[file_name][str(registro_idx)]["tipo"] = True
                progress[file_name][str(registro_idx)]["valor"] = True
                for person_idx in range(len(registro.alienantes)):
                    progress[file_name][str(registro_idx)][f"doc_alienante_{person_idx}"] = True
                for person_idx in range(len(registro.adquirentes)):
                    progress[file_name][str(registro_idx)][f"doc_adquirente_{person_idx}"] = True
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
            st.success("Progresso salvo com sucesso!")
        if st.button("Carregar Progresso"):
            st.session_state.progress = load_progress()
            st.success("Progresso carregado com sucesso!")
