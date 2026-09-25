-- Dated rule lookup. Payload lives in files/masters/rule_set.json and lms.rule_set.

CREATE SCHEMA IF NOT EXISTS fact;

CREATE OR REPLACE VIEW fact.rule_as_of AS
SELECT
    r.rule_code,
    r.product_code,
    r.effective_from,
    r.effective_to,
    r.payload
FROM lms.rule_set r;

-- Example: waterfall in force on a payment value_date
-- SELECT payload->>'order' FROM lms.rule_set
--  WHERE rule_code = 'WATERFALL'
--    AND product_code IN (:product, '*')
--    AND effective_from <= :value_date
--    AND (effective_to IS NULL OR effective_to >= :value_date)
--  ORDER BY (product_code = :product) DESC
--  LIMIT 1;
