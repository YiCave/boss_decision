-- Migration Script: Add UNIQUE Constraints for UPSERT Logic
-- Run this on existing database to add the constraints

-- Add UNIQUE constraint to hr_record (employee_id, period)
-- This prevents duplicate HR records for the same employee in the same period
ALTER TABLE hr_record 
ADD CONSTRAINT hr_record_employee_period_unique 
UNIQUE (employee_id, period);

-- Add UNIQUE constraint to supply_record (item_name, period)
-- This prevents duplicate supply records for the same item in the same period
ALTER TABLE supply_record 
ADD CONSTRAINT supply_record_item_period_unique 
UNIQUE (item_name, period);

-- Note: If you already have duplicate data, you'll need to clean it first:
-- 
-- Check for duplicates in hr_record:
-- SELECT employee_id, period, COUNT(*) 
-- FROM hr_record 
-- GROUP BY employee_id, period 
-- HAVING COUNT(*) > 1;
--
-- Check for duplicates in supply_record:
-- SELECT item_name, period, COUNT(*) 
-- FROM supply_record 
-- GROUP BY item_name, period 
-- HAVING COUNT(*) > 1;
