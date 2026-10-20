-- Propuesta de migración: revisar y aplicar manualmente por CE en el esquema
-- propietario del Conjunto Consultable. NO la ejecuta db_client.py.
-- No contiene secretos ni crea usuarios. No sustituye la tabla de Marco.
CREATE TABLE conjunto_consultable_meta (
    id NUMBER(1) PRIMARY KEY CHECK (id = 1),
    version VARCHAR2(10 CHAR) NOT NULL CHECK (version IN ('1.0', '1.1')),
    total NUMBER(10) NOT NULL CHECK (total >= 0 AND total = TRUNC(total)),
    total_spam_excluido NUMBER(10) NOT NULL
        CHECK (total_spam_excluido >= 0
               AND total_spam_excluido = TRUNC(total_spam_excluido))
);

-- El usuario del agente debe recibir SOLO CREATE SESSION y SELECT sobre
-- conjunto_consultable y conjunto_consultable_meta, nunca ser su propietario.
-- El DBA debe resolver los nombres en su esquema mediante sinónimos privados
-- o configurar CURRENT_SCHEMA en una conexión de lectura inyectada.
-- No otorgar CREATE TABLE, INSERT, UPDATE ni DELETE al usuario del agente.
