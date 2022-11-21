import streamlit as st
import pandas as pd
import numpy as np
import torch
import tokenizers
from inference_utils.fishbAIT_for_inference import fishbAIT

@st.cache(hash_funcs={
    tokenizers.Tokenizer: lambda _: None, 
    tokenizers.AddedToken: lambda _: None})
def loadmodel(version):
    fishbait = fishbAIT(model_version=version)
    fishbait.load_fine_tuned_model()
    return fishbait

def loadtokenizer(version):
    tokenizer = AutoTokenizer.from_pretrained(f'StyrbjornKall/fishbAIT_{version}')
    return tokenizer

# APP
st.sidebar.image("logo.jpg", use_column_width=True, caption='logo - Generated through DALL-E')
app_mode = st.sidebar.selectbox('Select Page',['Predict','Documentation'])
input_type = st.sidebar.checkbox("Batch (.csv) input", key="batch")
st.title('''fishbAIT''')
st.markdown('A deep learning software that lets you predict chemical ecotoxicity to fish')
endpoints = {'EC50': 'EC50', 'EC10': 'EC10'}
effects = {'MOR': 'MOR', 'DVP': 'DVP', 'GRO': 'GRO','POP': 'POP','MPH':'MPH'}
model_type = {'EC50': 'EC50','Chronic': 'EC10','Combined model': 'EC50EC10'}

PREDICTION_ENDPOINT = st.sidebar.radio("Select Endpoint ",tuple(endpoints.keys()))
PREDICTION_EFFECT = st.sidebar.radio("Select Effect ",tuple(effects.keys()))
modeltype = st.sidebar.radio("Select Model type", tuple(model_type.keys()))

if app_mode=='Predict': 
    if st.session_state.batch:
        file_up = st.file_uploader("Upload csv data containing SMILES, Duration, Effect & Endpoint", type="csv")
        
        if file_up:
            df=pd.read_csv(file_up, sep=';') #Read our data dataset
            processor = PreProcessDataForInference(df)
            processor.GetOneHotEnc(list_of_endpoints=[endpoint], list_of_effects=['MOR'])
            processor.GetCanonicalSMILES()
            df = processor.dataframe
            st.write(df.head())

        if st.button("Predict"):
            with st.spinner(text = 'Inference in Progress...'):
                
                st.write(
                    '<img width=100 src="http://static.skaip.org/img/emoticons/180x180/f6fcff/fish.gif" style="margin-left: 5px; brightness(1.1);">',
                    unsafe_allow_html=True,
                        )
                
                model = loadmodel(version=modeltype)
                tokenizer = loadtokenizer(version=model_type)
                loader = BuildInferenceDataLoader(
                    df=df, 
                    variables=['SMILES_Canonicalized_RDKit','exposure_duration','endpoint','effect'], 
                    tokenizer=tokenizer, 
                    batch_size=1).dataloader

                with torch.no_grad():
                    for _, batch in enumerate(loader):
                        out = np.round(model(
                            batch[0],
                            batch[1], 
                            batch[2], 
                            batch[3]
                            ).numpy(),2)
                st.balloons()
                result = df.copy()
                st.success(f'Predicted effect concentration(s):')
                result['Predictions [Log10(mg/L)]'], result['Predictions [mg/L]'] = out.tolist(), (10**out).tolist()
                st.write(result.head())

    elif ~st.session_state.batch:        
        st.text_input(
        "Input SMILES 👇",
        "C1=CC=CC=C1",
        key="smile",
        )
        
        EXPOSURE_DURATION = st.slider(
            'Select exposure duration (e.g. 96 h)',
            min_value=0, max_value=300, step=2)

        if st.button("Predict"):
            data = pd.DataFrame()
            data['SMILES'] = [st.session_state.smile]
            
            with st.spinner(text = 'Inference in Progress...'):
                fishbait = loadmodel(version=modeltype)
                
                results = fishbait.predict_toxicity(
                    SMILES = data.SMILES.tolist(), 
                    exposure_duration=EXPOSURE_DURATION, 
                    endpoint=PREDICTION_ENDPOINT, 
                    effect=PREDICTION_EFFECT)

                st.balloons()
                st.success(f'Predicted effect concentration(s):')
                st.write(results.head())



