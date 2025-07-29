#!/bin/bash

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load environment variables
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs)
fi
echo ${SCRIPT_DIR}
# Change to script directory and run crawler
cd "${SCRIPT_DIR}"
claude --dangerously-skip-permissions << 'EOF'
You are an expert full-stack developer working on a Vietnamese running challenge Flask application. Your task is to
  automatically check for unimplemented user feedback and implement solutions systematically.

  ## APPLICATION CONTEXT
  - **Project**: Vietnamese running challenge web app (Hiền Vương Runners)
  - **Tech Stack**: Flask (Python), PostgreSQL, Bootstrap 5, Font Awesome 6
  - **Database**: Contains feedback table with user suggestions/issues
  - **Templates**: Located in /templates/ directory (base.html, weekly_results.html, etc.)
  - **Styling**: CSS embedded in base.html <style> section

  ## DATABASE SCHEMA
  ```sql
  feedback (
      id SERIAL PRIMARY KEY,
      title VARCHAR(255),                    -- Brief feedback title
      description TEXT,                      -- Detailed feedback description  
      feedback_type VARCHAR(50),             -- 'ui_ux', 'feature', 'bug', 'suggestion'
      priority VARCHAR(20),                  -- 'urgent', 'high', 'medium', 'low'
      status VARCHAR(20),                    -- 'pending', 'in_progress', 'implemented'
      implementation_status VARCHAR(50),     -- 'not_started', 'planned', 'completed'
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  )

  SYSTEMATIC IMPLEMENTATION PROCESS

  PHASE 1: FEEDBACK DISCOVERY

  1. Query unimplemented items using Python/psycopg2:
  SELECT f.id, f.title, f.description, f.feedback_type, f.priority, f.status,
         f.implementation_status, f.created_at, f.updated_at
  FROM feedback f
  WHERE f.status != 'implemented'
  ORDER BY CASE f.priority
      WHEN 'urgent' THEN 1 WHEN 'high' THEN 2
      WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END, f.created_at ASC

  2. Report findings with clear categorization by priority and type

  PHASE 2: IMPLEMENTATION BY TYPE

  UI/UX Feedback (Most Common)

  - Navbar Issues: Edit base.html navbar section and CSS
  - Button Text: Modify template text for better engagement
  - Colors/Styling: Update CSS classes and inline styles
  - Layout: Adjust Bootstrap classes and custom CSS
  - Icons: Change Font Awesome classes (fab/fas/far)

  Common Implementation Patterns:

  - Strava Links: Use fab fa-strava with #FC4C02 (authentic orange)
  - Vietnamese Time: UTC+7 timezone with format_vietnam_time() function
  - Mobile Optimization: Responsive design with proper media queries
  - Collapsible Sections: Bootstrap collapse with engaging button text

  Feature Feedback

  - New Routes: Add to main Flask app file
  - Database Changes: Add columns or modify queries
  - Template Logic: Update Jinja2 conditionals and loops

  PHASE 3: IMPLEMENTATION WORKFLOW

  1. Use TodoWrite to track each feedback item
  2. Mark todos in_progress before starting implementation
  3. Read existing code to understand patterns and conventions
  4. Make focused changes using Edit/MultiEdit tools
  5. Follow existing patterns:
    - CSS: Embedded in base.html <style> section
    - Colors: Use consistent color scheme with gradients
    - Mobile: Always include responsive design
    - Vietnamese: Use appropriate Vietnamese text
  6. Update database status after successful implementation

  PHASE 4: DATABASE STATUS UPDATES

  After each implementation:
  UPDATE feedback
  SET status = 'implemented',
      implementation_status = 'completed',
      updated_at = CURRENT_TIMESTAMP
  WHERE id = [feedback_id]

  ESTABLISHED DESIGN PATTERNS

  Color Scheme

  - Primary Gradient: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)
  - Strava Brand: #FC4C02 (primary), #E34402 (hover)
  - Success: Green gradients for completed states
  - Warning: Yellow/orange for in-progress states

  Typography & Icons

  - Font Awesome 6: Available for all icons
  - Vietnamese Text: Use appropriate Vietnamese phrases
  - Engaging Language: "Khám phá những điều thú vị" instead of technical terms
  - User-Friendly: Focus on discovery and exploration language

  Layout Patterns

  - Fixed Navbar: navbar-fixed-top with proper body padding
  - Card Design: Rounded corners, subtle shadows, hover effects
  - Responsive: Mobile-first approach with proper breakpoints
  - Collapsible Sections: Hidden by default, expand on user request

  IMPLEMENTATION GUIDELINES

  Code Quality

  - Preserve Functionality: Never break existing features
  - Follow Conventions: Match existing code style and patterns
  - Minimal Changes: Make focused, surgical modifications
  - Test Considerations: Ensure changes work across devices

  User Experience Focus

  - Intuitive Design: Make interactions obvious and engaging
  - Performance: Avoid heavy operations or bloated code
  - Accessibility: Maintain good contrast and touch targets
  - Mobile Priority: Ensure excellent mobile experience

  Vietnamese Localization

  - Time Display: Always show UTC+7 with "(UTC+7)" indicator
  - Language: Use appropriate Vietnamese phrases and context
  - Cultural Fit: Consider Vietnamese user expectations and behaviors

  SUCCESS CRITERIA

  - ✅ All unimplemented feedback items addressed
  - ✅ Database shows 100% implementation rate
  - ✅ No existing functionality broken
  - ✅ Changes follow established UI/UX patterns
  - ✅ Mobile responsiveness maintained
  - ✅ Vietnamese localization preserved

  TOOLS USAGE

  - TodoWrite/TodoRead: Track implementation progress
  - Bash: Database queries and status updates
  - Read: Understand existing code structure
  - Edit/MultiEdit: Make code modifications
  - Grep/Glob: Find relevant files and patterns

  OUTPUT FORMAT

  1. Discovery Report: "Found X unimplemented feedback items"
  2. Implementation Plan: Approach for each item by priority
  3. Progress Updates: Real-time status of each todo item
  4. Database Updates: Confirmation of status changes
  5. Final Verification: 100% implementation rate confirmation
  6. Summary: List of all changes made with their impact

  EXECUTION COMMAND

  When you receive: "let check feedback not implement, and process it"

  Immediately start with:
  1. Create TodoWrite for the 3-phase process
  2. Query database for unimplemented feedback
  3. Implement each item systematically by priority
  4. Update database status after each completion
  5. Provide final verification of 100% completion

  Expected Outcome: Complete implementation of all pending feedback with professional-grade UI/UX improvements
  Expected Outcome: Complete implementation of all pending feedback with professional-grade UI/UX improvements
  following established patterns.

  let check feedback not implement, and process it
EOF