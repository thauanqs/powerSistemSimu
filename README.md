# powerSistemSimu
Simulador de sistemas de potência.


# Instruções e dependências
Usar Python 3.12.

ABRA O CMD NA PASTA ONDE QUER BAIXAR O PROJETO E EXECUTE:

    git clone https://github.com/thauanqs/powerSistemSimu.git


Agora, dentro da nova pasta "powerSistemSimu" que foi criada execute no CMD:

    py -m venv .venv
    py -3.12 -m venv .venv
    .venv\Scripts\activate


Instalar as dependências usando:

    py -m pip install -r requirements.txt

# Gerando arquivo executável Windows

Atenção: os passos a seguir devem ser feitos também com o ambiente virtual ativado (.env).

Para gerar um executável Windows, com o venv ativo, navegue até a pasta "src":

    cd src

e execute:

    pyinstaller --onefile --noconsole main.py

O arquivo executável será criado como maim.exe na pasta "powerSistemSimu\src\dist"


# Abrir exemplos no formato IEEE (.txt)
Selecionar: Project > Open IEEE

Os exemplos estão localizados em:   
    powerSistemSimu\assets\ieee_examples


