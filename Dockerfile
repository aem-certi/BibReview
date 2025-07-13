FROM python:3.12-slim

# Ambiente
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalação de dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o pacote revsys em modo editável
COPY setup.py .
COPY src/ src/
RUN pip install --no-cache-dir -e .

# Ponto de entrada padrão
ENTRYPOINT ["revsys"]
CMD ["--help"]