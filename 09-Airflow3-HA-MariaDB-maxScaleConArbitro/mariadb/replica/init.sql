-- ============================================================================
-- MARIADB REPLICA - SAN LORENZO
-- ============================================================================
-- Configuración de replicación desde primary (nombres simples como caso 08)
-- ============================================================================

-- Configurar replicación desde el primary
CHANGE MASTER TO
    MASTER_HOST='172.20.0.20',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;

-- Esperar sincronización inicial
SELECT SLEEP(10);

-- Log de inicialización
SELECT 'REPLICA SAN LORENZO INITIALIZED' as status;
