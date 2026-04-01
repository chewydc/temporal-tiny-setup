-- ============================================================================
-- MARIADB REPLICA - SAN LORENZO
-- ============================================================================
-- Configuración de replicación desde primary (nombres simples como caso 08)
-- ============================================================================

-- Configurar replicación desde el primary
SET GLOBAL gtid_slave_pos = '';
CHANGE MASTER TO
    MASTER_HOST='172.20.0.20',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;

-- Verificar estado de replicación
SELECT SLEEP(10);
SHOW SLAVE STATUS\G

-- Log de inicialización
SELECT 'REPLICA SAN LORENZO INITIALIZED' as status;
