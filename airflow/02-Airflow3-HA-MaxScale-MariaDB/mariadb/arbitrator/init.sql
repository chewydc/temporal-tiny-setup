-- ============================================================================
-- MARIADB ARBITRATOR - TUCUMAN (RED ÚNICA SIMPLIFICADA)
-- ============================================================================

-- CRÍTICO: Configurar como read-only ANTES de la replicación
SET GLOBAL read_only = 1;

CHANGE MASTER TO
    MASTER_HOST='mariadb-hornos',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;

-- Esperar a que la replicacion sincronice los usuarios del primary
SELECT SLEEP(5);
