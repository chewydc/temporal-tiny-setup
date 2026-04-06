-- ============================================================================
-- MARIADB REPLICA - SAN LORENZO
-- ============================================================================
-- Configuración de replicación desde primary (preparada para failover)
-- IMPORTANTE: NO configurar read_only para permitir promoción automática
-- ============================================================================

-- Esperar a que el primary esté completamente listo y Airflow inicializado
SELECT SLEEP(30);

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

-- Verificar estado de replicación
SELECT SLEEP(10);
SHOW SLAVE STATUS\G

-- Log de inicialización
SELECT 'REPLICA SAN LORENZO INITIALIZED - READY FOR FAILOVER' as status;
