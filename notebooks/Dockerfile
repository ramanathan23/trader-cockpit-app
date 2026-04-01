FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    jupyterlab \
    pandas \
    numpy \
    sqlalchemy \
    psycopg2-binary \
    asyncpg \
    plotly \
    matplotlib \
    vectorbt \
    ipywidgets \
    python-dotenv

EXPOSE 8888

CMD ["jupyter", "lab", \
     "--ip=0.0.0.0", \
     "--port=8888", \
     "--no-browser", \
     "--allow-root", \
     "--notebook-dir=/app/notebooks", \
     "--NotebookApp.token=''"]
