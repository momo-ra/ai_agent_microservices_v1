-- Migration: Add chat_name and is_starred fields to chat_sessions table
-- Date: 2025-01-11
-- Description: Adds user-defined chat names and starring functionality

-- Add the new columns
ALTER TABLE chat_sessions 
ADD COLUMN IF NOT EXISTS chat_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_is_starred ON chat_sessions(is_starred);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at);

-- Update existing records to have default values
UPDATE chat_sessions 
SET is_starred = FALSE 
WHERE is_starred IS NULL;

-- Make is_starred NOT NULL after setting defaults
ALTER TABLE chat_sessions 
ALTER COLUMN is_starred SET NOT NULL;

-- Add a comment to document the changes
COMMENT ON COLUMN chat_sessions.chat_name IS 'User-defined name for the chat session';
COMMENT ON COLUMN chat_sessions.is_starred IS 'Whether the chat session is starred/favorited by the user';
