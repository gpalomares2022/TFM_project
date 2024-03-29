import logging
import random
import warnings
import pandas as pd
import numpy as np
from kedro.config import ConfigLoader, MissingConfigException






logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

#Función interna para hacer lectura de CSV
def _load_from_csv (path):
    data=pd.read_csv(path)
    return data  

#Función interna que te dice si una lista tiene elementos repetidos
def _no_hay_repetidos(listNums):
  s=set (listNums)
 
  return len(s)==len(listNums)

#Función interna que desordenada de posición los elementos de una lista
def _desordenar(lista):
    return random.sample(lista, len(lista))

# Genera un CSV con todas las enfermedades registradas (sin repetir), dado un datafame con el registro de enfermedades y síntomas existentes

def _generate_data_enfermedades (df_enfermedades_con_sintoma: pd.DataFrame):

    
    df_Enfermedades=df_enfermedades_con_sintoma.groupby (["Enfermedad"]).count().reset_index()
    df_Enfermedades=df_Enfermedades.drop(["Sintoma","Frecuencia"], axis=1)
    df_Enfermedades=df_Enfermedades.reset_index()

    return df_Enfermedades
#------------------------------------------------------------------------------------------------------#

#Función que dado un listado de enfermedades y scoring, monta un listado completo con Frecuencia, Scoring... Es una función para visualización
def _monta_listado (scoring_enfermedades,id_Sintoma, df_Enfermedades, df_Sintomas,df_EnfeySinto_select):
    
    
    
    j=0
    enfermedades=[]
    while (j<len(scoring_enfermedades)):
        enfermedad=[]
        id_enfermedad=scoring_enfermedades["index"][j]
        scoring=scoring_enfermedades[id_Sintoma][j]
        
        enfermedad.append(id_enfermedad)
        
       
        enfermedad.append(df_Enfermedades[df_Enfermedades["index"]==id_enfermedad]["Enfermedad"].values[0])
   
        enfermedad.append(str(scoring))
        lista=df_EnfeySinto_select[df_EnfeySinto_select["Enfermedad"]==
                                   df_Enfermedades.loc[id_enfermedad][1]]
        lista=lista.reset_index()
        sintoma= df_Sintomas.loc[id_Sintoma].Sintoma
        enfermedad.append(sintoma)
        i=0
        while i<len(lista):
         
            if lista["Sintoma"][i]==sintoma:
                enfermedad.append(lista["Frecuencia"][i])
            
            i=i+1  
        j=j+1
        enfermedades.append(enfermedad)
        df_enfermedades=pd.DataFrame(enfermedades)
        
    return df_enfermedades




#------------------------------------------------------------------------------------------------------#

#Función interna que recibe un Síntoma concreto y devuelve un listado de X enfermedades recomendadas (por scoring de mayor a menor)
def recommendation_collaborative_filtering_user_based( sintoma,
                                              df_Sintomas: pd.DataFrame, df_Enfermedades: pd.DataFrame, 
                                              df_EnfeySinto_select: pd.DataFrame):
  
    

    #leemos el parámetro elementos, con el que vamos a sacar la lista de recomendados
    conf_path = str("conf/")
    conf_loader = ConfigLoader(conf_source=conf_path)
  
    try:
        parameters = conf_loader["parameters"]
    except MissingConfigException:
        parameters = {}

    elementos=parameters["elementos"]

   
    #Obtenemos el id del Síntoma (en el CSV de Síntomas) a partir del nombre. Es necesario para poder operar.
    id_sintoma = df_Sintomas[df_Sintomas['Sintoma'] == sintoma].index.values[0]

    #Cargamos las recomendaciones que se hicieron en pipeline de Procesamiento
    df_recomendaciones=_load_from_csv("data/04_feature/df_recommendations.csv")
    #Convertioms a numpy para operar
    df_recomendaciones=df_recomendaciones.to_numpy()
    
    
    #Cargamos los índices dado el id_sintoma. Aquí tendríamos los índices de las enfermedades 
    enfermedades=df_recomendaciones.argsort()[id_sintoma]
    vector_id_enfermedad_scoring=[]
    #Inicializamos nuestro vector TOTAL que tendrá las parejas de "enfermedad" /scoring de recomendación
    #(valor en la matriz recomendaciones)
    for  i,id_enfermedad in enumerate(enfermedades[-elementos:]):
        #Ahora recorremos las enfermedades asociadas y vamos guardando. Nos quedamos con los X elementos.
        vector_enfermedades=[]
        enfermedad = df_Enfermedades[df_Enfermedades["index"]==id_enfermedad]
  
        vector_enfermedades.append (id_enfermedad)
        vector_enfermedades.append (df_recomendaciones[id_sintoma][id_enfermedad])
        vector_enfermedades.append (sintoma)
        vector_id_enfermedad_scoring.append(vector_enfermedades)
        
    vector_id_enfermedad_scoring=pd.DataFrame(vector_id_enfermedad_scoring)
    vector_id_enfermedad_scoring = vector_id_enfermedad_scoring.rename(columns={1:id_sintoma, 0:"index"})
    
    #utilizamos la función "_aparece_y_como" para montar el listado completo y correcto.
    listado_completo=_monta_listado (vector_id_enfermedad_scoring,id_sintoma, df_Enfermedades, df_Sintomas,df_EnfeySinto_select)
    listado_completo=listado_completo.rename(columns={1: "Enfermedad", 2: "Scoring", 3: "Síntomas", 4: "Frecuencia"})
    listado_completo=listado_completo.sort_values("Scoring", ascending=False)
    listado_completo=listado_completo.reset_index()
    listado_completo.drop("index", axis=1, inplace=True)
 
    return listado_completo

#------------------------------------------------------------------------------------------------------#

#Función llamada desde el Recomendador.py de la Interfaz Web vía Streamlit. Es la que recibirá el listado de síntomas seleccionados en el desplegable (multi-seleccionable)
#y devolverá un listado modo ranking con las enfermedades recomendados, cómo aparecen dichas enfermedades en los síntomas que se han seleccionado, y un scoring
#que clasifica

def llamada_recomendador (sintomas):

    #Cargamos las enfermedades, los sintomas y el listado que contiene la tupla enfermedad-síntoma-frecuencia (ya con eda pasado)
    df_enfermedades= _load_from_csv("data/03_primary/enfermedades.csv")
    df_sintomas= _load_from_csv("data/03_primary/sintomas.csv")
    df_sintomas_enfermedades_eda=_load_from_csv("data/02_intermediate/sintomas_and_enfermedades_prepaired_post_eda.csv")
   
    #Preparamos un listado que acumulará todas las enfermedades recomendadas de cada síntoma    
    enfermedades_scoring=[]
    enfermedades_scoring=pd.DataFrame(enfermedades_scoring)
  
    i=0
    #Para cada uno de los sintomas que recibimos en la lista "sintomas"
    for i in sintomas:    
        #Llamamos a la función _predict_collaborative_filtering_ser_based con cada uno de los síntomas.
        #Ésta nos va a devolver, para cada síntoma, un listado de X enfermedades recomendadas (por scoring de mayor a menor)
        enfermedades_predecidas=recommendation_collaborative_filtering_user_based(i,df_sintomas,df_enfermedades,df_sintomas_enfermedades_eda)
     
        #Generamos Dataframe con el listado recibido, y eliminamos nulos
        enfermedades_predecidas=pd.DataFrame(enfermedades_predecidas)
        enfermedades_predecidas=enfermedades_predecidas.dropna()

        #Vamos agrupando en enfermedades_scoring todas las enfermedades recogidas. Sin ningún filtro, únicamente "metemos en el saco" de lo que se ha ido recomendado
        #para cada síntoma. Vamos también limpiando nulos por si hay error.
        enfermedades_scoring=pd.concat([enfermedades_scoring,enfermedades_predecidas], axis=0)
        enfermedades_scoring=enfermedades_scoring.dropna()
        
  
    #Hemos terminado de agrupar todas las enfermedades recomendadas por cada síntoma.
    #Si este listado no está vacío montamos el ranking!! 
    
    if len(enfermedades_scoring)>0:
     
        #Generamos una agrupación de Enfermedad, los síntomas que hemos marcado en los que aparece, su frecuencia, y el scoring
        data_agrupado = (enfermedades_scoring.groupby("Enfermedad")
         .agg({"Frecuencia": np.array, "Scoring": np.double, "Síntomas": np.array})
         .reset_index()
         )
       
        enfermedades_suma=[]
        i=0
        
        #Con este while montamos el listado más completo, de tal forma que mostramos Enfermedad, los síntomas asociados a la enfermedad (que se hayan seleccionado
        # en el desplegable), junto al síntoma el scoring que posee de recomendación con la enfermedad. Y luego un scoring global (sumatoria)
        while (i<len(data_agrupado)):
             enfermedad_suma=[]
             enfermedad_suma.append (data_agrupado["Enfermedad"][i])

             sintomas_para_sumar=data_agrupado["Scoring"][i]
             nombre_sintoma=data_agrupado["Síntomas"][i]
             
             if (type(sintomas_para_sumar)==np.float64):
                g=[]
                total=round(sintomas_para_sumar,3)
                g.append(nombre_sintoma[0] + " ("+ str(total) + ")")
                num_sintomas=1

             else:
                 j=0
                 total=0
                 num_sintomas=len(sintomas_para_sumar)
                 g=[]
                 while (j<num_sintomas):
                     valor= round(sintomas_para_sumar[j],3)
                     g.append(nombre_sintoma[j] + " ("+ str(valor) + ")")
                     total=sintomas_para_sumar[j]+total
                     j=j+1
             enfermedad_suma.append(g)
             enfermedad_suma.append(total)
             enfermedades_suma.append(enfermedad_suma)
            
             i=i+1
      
        #Damos el último formato al listado ranking
        df_enfermedades_suma=pd.DataFrame (enfermedades_suma)
        df_enfermedades_suma = df_enfermedades_suma.rename(columns={1:"Síntomas", 0:"Enfermedad", 2:"Scoring"})
        df_enfermedades_suma=df_enfermedades_suma.sort_values(by="Scoring", ascending=False)
        df_enfermedades_suma=df_enfermedades_suma.reset_index()
        df_enfermedades_suma.drop("index", axis=1, inplace=True)
      
    else:
        #Si no se han incluido síntomas, devolvemos listado vacío
       
        df_enfermedades_suma=pd.DataFrame()

 
    return  df_enfermedades_suma


#------------------------------------------------------------------------------------------------------#

#Función llamada desde el Evaluacion.py de la Interfaz Web vía Streamlit. Es la que recibirá un único sintoma seleccionado en el desplegable
#y devolverá un listado con los nombres de 10 enfermades: 5 primeras recomendadas por nuestro algoritmo, y 5 aleatorias. 
# Se devolverán mezcladas.
#También devolvemos, para trabajo, el listado únicamente de las 5 recomendadas
def llamada_recomendador_metrica (sintoma):

    #Cargamos las enfermedades, los sintomas y el listado que contiene la tupla enfermedad-síntoma-frecuencia (ya con eda pasado)
    df_enfermedades= _load_from_csv("data/03_primary/enfermedades.csv")
    df_sintomas= _load_from_csv("data/03_primary/sintomas.csv")
    df_sintomas_enfermedades_eda=_load_from_csv("data/02_intermediate/sintomas_and_enfermedades_prepaired_post_eda.csv")
   
    
    #Llamamos a la función _predict_collaborative_filtering_ser_based el síntoma recibido.
    #Ésta nos va a devolver un listado de X enfermedades recomendadas (por scoring de mayor a menor)
    enfermedades_predecidas=recommendation_collaborative_filtering_user_based(sintoma,df_sintomas,df_enfermedades,df_sintomas_enfermedades_eda)
    #nos quedamos con las cinco primeras
    enfermedades_predecidas_primeras_cinco=enfermedades_predecidas.head(5) 
    lista_enfermedades_predecidas_primeras_cinco=enfermedades_predecidas_primeras_cinco.to_numpy().transpose().tolist()   
    lista_enfermedades_predecidas_primeras_cinco=list(lista_enfermedades_predecidas_primeras_cinco[1])
    #Las hemos pasado a lista para trabajar con ellas y return.

    #Comenzamos a montar también la lista con las 10 enfermedades. Nos quedamos con las 5 recomendadas 
    
    lista_diez_enfermedades=enfermedades_predecidas_primeras_cinco.to_numpy().transpose().tolist()   
    lista_diez_enfermedades=list(lista_diez_enfermedades[1])
    #y ahora vamos a cargar las aleatorias de todo el listado de enfermedades. Los cargamos y vamos cogiendo.
    #Es importante comentar que, dado que nos viene un síntoma marcado, el listado de enfermedades aleatorias viene
    #filtrado por enfermedades que tienen este síntoma también.
    #Cogemos primero el df que tiene el registro de enfermedades-sintomas, y nos quedamos con los datos de enfermedades-sintomas 
    #donde el sintoma es el seleccionado.
    df_sintomas_enfermedades_con_sintoma_selec=df_sintomas_enfermedades_eda[df_sintomas_enfermedades_eda["Sintoma"]==sintoma]

    #Ahora ya tenemos el registro de enfermedades y síntomas, pero filtrado por sintoma seleccionado. Vamos a obtener un listado
    #normal de enfermedades (sólo enfermedades y sin repetir)
    
    df_enfermedades_con_sintoma_select=_generate_data_enfermedades (df_sintomas_enfermedades_con_sintoma_selec)
  

    #El df obtenido lo convertimos a Lista para trabajar con él.
    listado_enfermedades_sistema=df_enfermedades_con_sintoma_select.to_numpy().transpose().tolist()   
    listado_enfermedades_sistema=listado_enfermedades_sistema[1]
    
    i=0
    while (i<5):
        valor=  random.randint(0, len(listado_enfermedades_sistema))
        lista_diez_enfermedades.append(listado_enfermedades_sistema[valor])
        if (not _no_hay_repetidos(lista_diez_enfermedades)):
            #Verificamos que, por casualidad, se ha calculado aleatoriamente una enfermedad que ya estaba incluida por el recomendador 
            #o por un random anterior. Si es así, la quitamos y volvemos a cargar.
          
            del lista_diez_enfermedades[5+i]
        else:
            
 
            i=i+1 
    #salen las 5 primeras las recomendadas, y las 5 siguientes las aleatorias. Desordenamos para el experimento
    lista_diez_enfermedades=_desordenar(lista_diez_enfermedades)

   
 

 
    return  lista_diez_enfermedades,lista_enfermedades_predecidas_primeras_cinco







