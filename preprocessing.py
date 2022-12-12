import subprocess


def translate(string):
    result = subprocess.run("curl https://api-free.deepl.com/v2/translate -d auth_key=c81eb10f-2c77-5196-2fdc-1b0d40f7da39:fx -d \"text="+string+"\"  -d \"target_lang=EN\"", shell = True, stdout=subprocess.PIPE)
    translated = result.stdout.decode('utf-8')
    translated = translated.partition("\"text\":")[2]
    translated = translated.partition("}]}")[0]
    translated = translated.lstrip('"').rstrip('"')

    return translated

def translated(df):
    df['text']= df['text'].apply(lambda x: translate(x))
    df.to_csv('translated_data(3).csv')

    return df