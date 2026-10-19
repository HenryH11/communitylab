import os


# Evita que la suite escriba en salida/logs; las pruebas usan caplog.
os.environ.setdefault("COMMUNITYLAB_LOGS", "0")
