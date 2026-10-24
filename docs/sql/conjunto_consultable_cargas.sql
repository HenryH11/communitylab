-- Propuesta: ejecutar manualmente como propietario de las tablas, después
-- de revisión de CE. No se aplica automáticamente desde Python.
-- La identidad pública de Marketing NO necesita acceso a esta tabla.
CREATE TABLE conjunto_consultable_cargas (
    huella VARCHAR2(64 CHAR) PRIMARY KEY,
    version VARCHAR2(10 CHAR) NOT NULL,
    total NUMBER(10) NOT NULL CHECK (total >= 0),
    total_spam_excluido NUMBER(10) NOT NULL
        CHECK (total_spam_excluido >= 0),
    creada_en TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);
