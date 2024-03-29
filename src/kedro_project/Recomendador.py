import streamlit as st
import pandas as pd
from pipelines.data_science import nodes


#Función interna para hacer lectura de CSV
def load_from_csv (path):
    data=pd.read_csv(path)
    return data  


#------------------------------------------------------------------------------------------------------#
#Limpiamos sesión
if 'sintoma' in st.session_state: 
        del st.session_state.sintoma
       
#INSTRUCCIONES PARA STREAMLIT INTERFAZ WEB

#Leemos los Síntomas existentes para que sean cargados en el multiselect de Streamlit (combo multiseleccionable)
df_sintomas= load_from_csv("data/03_primary/sintomas.csv")


st.sidebar.header("TFM Máster Data Science - KSchool - Gabriel Palomares")

st.sidebar.header ("Sistemas Recomendador de Enfermedades raras")



button_press = st.sidebar.button("Pulsa para comenzar Análisis y Recomendador")

options = st.sidebar.multiselect(
            'Seleccione aquí los síntomas del paciente, y luego pulse el botón superior para comenzar el análisis y recomendación.',
            df_sintomas,
            [])
#Incluimos el botón para comenzar el Analísis y Recomendación. 



if (button_press):
    #Una vez pulsado el botón, se agrupan todos los síntomas marcados y se realiza la llamada al recomendador 
    sintomas=[]
    for i in options: #
        sintomas.append(i)
    
    #La función llamada recomendador recoge todo los sintomas, analiza una recomendación conjunta para todos ellos y devuelve un listado ranking listo para visualizar
    ranking=nodes.llamada_recomendador(sintomas)


    #Finalmente,se pinta en pantalla el listado que ha montado la función llamada_recomendador
    st.dataframe(ranking,3800,6000)
    if 'sintoma' in st.session_state: 
        del st.session_state.sintoma
