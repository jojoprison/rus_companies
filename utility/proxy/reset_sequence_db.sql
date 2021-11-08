SELECT nextval(PG_GET_SERIAL_SEQUENCE('"proxy"', 'id'));

SELECT
    CURRVAL(PG_GET_SERIAL_SEQUENCE('"proxy"', 'id')) AS "Current Value",
    MAX("id") AS "Max Value"
FROM "proxy";

SELECT SETVAL(
    (SELECT PG_GET_SERIAL_SEQUENCE('"proxy"', 'id')),
    1,
    FALSE);