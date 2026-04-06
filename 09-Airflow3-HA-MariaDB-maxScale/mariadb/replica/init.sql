-- ============================================================================
-- MARIADB REPLICA - SAN LORENZO (RED ÚNICA SIMPLIFICADA)
-- ============================================================================

-- Esperar a que el primary esté listo
SELECT SLEEP(30);

-- Configurar replicación desde el primary
CHANGE MASTER TO
    MASTER_HOST='mariadb-hornos',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;

-- Verificar estado
SELECT SLEEP(10);
SHOW SLAVE STATUS\G

SELECT 'REPLICA SAN LORENZO INITIALIZED - READY FOR FAILOVER' as status;