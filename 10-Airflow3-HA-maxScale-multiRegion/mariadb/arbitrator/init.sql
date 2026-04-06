-- ============================================================================
-- MARIADB ARBITRATOR - TUCUMAN (NUNCA MASTER)
-- ============================================================================
-- Este nodo SOLO sirve para desempate en split-brain
-- NUNCA puede ser promovido a master
-- ============================================================================

-- Esperar a que el primary esté completamente listo y Airflow inicializado
SELECT SLEEP(35);

-- Configurar replicación desde el primary usando GTID automático
-- slave_pos permite que MariaDB maneje automáticamente la posición GTID
CHANGE MASTER TO
    MASTER_HOST='172.20.0.20',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_pass',
    MASTER_CONNECT_RETRY=10,
    MASTER_USE_GTID=slave_pos;

START SLAVE;

-- Configurar como read-only permanente
SET GLOBAL read_only = ON;

-- Verificar estado
SELECT SLEEP(10);
SHOW SLAVE STATUS\G

-- Log de inicialización
SELECT 'ARBITRATOR TUCUMAN INITIALIZED - READ ONLY' as status;