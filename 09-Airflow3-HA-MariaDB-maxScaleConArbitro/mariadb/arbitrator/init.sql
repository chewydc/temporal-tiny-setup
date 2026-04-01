-- ============================================================================
-- MARIADB ARBITRATOR - TUCUMAN (NUNCA MASTER)
-- ============================================================================
-- Este nodo SOLO sirve para desempate en split-brain
-- NUNCA puede ser promovido a master
-- ============================================================================

-- Configurar replicación desde el primary (solo para sincronizar usuarios)
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

-- Esperar sincronización inicial
SELECT SLEEP(15);

-- Log de inicialización
SELECT 'ARBITRATOR TUCUMAN INITIALIZED - READ ONLY' as status;