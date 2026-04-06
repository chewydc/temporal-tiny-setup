-- ============================================================================
-- MARIADB ARBITRATOR - TUCUMAN (RED ÚNICA SIMPLIFICADA)
-- ============================================================================

-- Esperar a que el primary esté listo
SELECT SLEEP(35);

-- Configurar replicación desde el primary
CHANGE MASTER TO
    MASTER_HOST='mariadb-hornos',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;

-- Configurar como read-only permanente (nunca puede ser master)
SET GLOBAL read_only = ON;

-- Verificar estado
SELECT SLEEP(10);
SHOW SLAVE STATUS\G

SELECT 'ARBITRATOR TUCUMAN INITIALIZED - READ ONLY' as status;