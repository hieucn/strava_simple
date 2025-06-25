#!/usr/bin/env python3
"""
AI Feature Generator for Vietnamese Running Challenge App
Analyzes user feedback and generates implementation plans and code
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

class AIFeatureGenerator:
    """AI-powered feature generator based on user feedback"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.logger = logging.getLogger(__name__)
        
    def get_db_connection(self):
        """Get database connection with dict cursor"""
        conn = psycopg2.connect(self.database_url)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    
    def analyze_feedback(self, feedback_data: Dict) -> Dict:
        """Analyze feedback and categorize implementation complexity"""
        
        title = feedback_data.get('title', '').lower()
        description = feedback_data.get('description', '').lower()
        feedback_type = feedback_data.get('feedback_type', 'suggestion')
        priority = feedback_data.get('priority', 'medium')
        
        # Categorize by complexity and type
        complexity = self._assess_complexity(title, description, feedback_type)
        implementation_type = self._determine_implementation_type(title, description)
        estimated_effort = self._estimate_effort(complexity, implementation_type)
        
        return {
            'complexity': complexity,
            'implementation_type': implementation_type,
            'estimated_effort': estimated_effort,
            'auto_implementable': complexity in ['low', 'medium'] and implementation_type in ['ui', 'content', 'stats']
        }
    
    def _assess_complexity(self, title: str, description: str, feedback_type: str) -> str:
        """Assess implementation complexity based on content analysis"""
        
        # Keywords that indicate different complexity levels
        low_complexity_keywords = [
            'màu sắc', 'color', 'font', 'text', 'hiển thị', 'display', 'show', 'hide',
            'thêm cột', 'add column', 'badge', 'icon', 'tooltip', 'css', 'style'
        ]
        
        medium_complexity_keywords = [
            'dashboard', 'thống kê', 'stats', 'chart', 'graph', 'filter', 'sort',
            'search', 'notification', 'email', 'export', 'import', 'api'
        ]
        
        high_complexity_keywords = [
            'authentication', 'security', 'payment', 'integration', 'machine learning',
            'ai', 'algorithm', 'real-time', 'websocket', 'microservice'
        ]
        
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in high_complexity_keywords):
            return 'high'
        elif any(keyword in text for keyword in medium_complexity_keywords):
            return 'medium'
        elif any(keyword in text for keyword in low_complexity_keywords):
            return 'low'
        else:
            # Default based on feedback type
            if feedback_type == 'bug':
                return 'low'
            elif feedback_type in ['suggestion', 'improvement']:
                return 'medium'
            else:
                return 'medium'
    
    def _determine_implementation_type(self, title: str, description: str) -> str:
        """Determine what type of implementation is needed"""
        
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ['ui', 'giao diện', 'màu sắc', 'style', 'css', 'design']):
            return 'ui'
        elif any(keyword in text for keyword in ['database', 'data', 'dữ liệu', 'store', 'save']):
            return 'database'
        elif any(keyword in text for keyword in ['api', 'integration', 'strava', 'external']):
            return 'api'
        elif any(keyword in text for keyword in ['thống kê', 'stats', 'dashboard', 'chart', 'report']):
            return 'stats'
        elif any(keyword in text for keyword in ['content', 'text', 'nội dung', 'hiển thị']):
            return 'content'
        else:
            return 'feature'
    
    def _estimate_effort(self, complexity: str, implementation_type: str) -> str:
        """Estimate development effort in person-hours"""
        
        base_effort = {
            'low': 2,
            'medium': 8,
            'high': 24
        }
        
        type_multiplier = {
            'ui': 1.0,
            'content': 0.5,
            'stats': 1.5,
            'database': 2.0,
            'api': 2.5,
            'feature': 1.0
        }
        
        hours = base_effort.get(complexity, 8) * type_multiplier.get(implementation_type, 1.0)
        
        if hours <= 4:
            return f"{hours:.0f} giờ"
        elif hours <= 24:
            return f"{hours/8:.1f} ngày"
        else:
            return f"{hours/40:.1f} tuần"
    
    def generate_implementation_plan(self, feedback_data: Dict) -> str:
        """Generate detailed implementation plan based on feedback"""
        
        analysis = self.analyze_feedback(feedback_data)
        
        plan_template = self._get_plan_template(feedback_data, analysis)
        
        # Generate specific implementation steps
        implementation_steps = self._generate_implementation_steps(feedback_data, analysis)
        
        # Generate code examples if applicable
        code_examples = self._generate_code_examples(feedback_data, analysis)
        
        # Generate testing plan
        testing_plan = self._generate_testing_plan(feedback_data, analysis)
        
        plan = f"""
AI IMPLEMENTATION PLAN - Generated at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
{'='*80}

📋 FEEDBACK ANALYSIS
Title: {feedback_data['title']}
Type: {feedback_data['feedback_type']}
Priority: {feedback_data['priority']}
Complexity: {analysis['complexity']}
Implementation Type: {analysis['implementation_type']}
Estimated Effort: {analysis['estimated_effort']}
Auto-Implementable: {'✅ Yes' if analysis['auto_implementable'] else '❌ No - Manual Review Required'}

📝 USER REQUEST
{feedback_data['description']}

🎯 IMPLEMENTATION STRATEGY
{plan_template}

🔧 DETAILED IMPLEMENTATION STEPS
{implementation_steps}

💻 CODE EXAMPLES
{code_examples}

🧪 TESTING PLAN
{testing_plan}

📦 DEPLOYMENT CHECKLIST
□ Code implementation completed
□ Unit tests written and passing
□ Integration tests completed
□ UI/UX review completed
□ Performance impact assessed
□ Security review (if applicable)
□ Documentation updated
□ Backup created before deployment
□ Deployment to staging environment
□ User acceptance testing
□ Production deployment
□ Post-deployment monitoring

🚀 DEPLOYMENT NOTES
- Backup database before implementing database changes
- Test in staging environment first
- Monitor application performance after deployment
- Rollback plan: [Specific to implementation type]

💡 RECOMMENDATIONS
{self._generate_recommendations(feedback_data, analysis)}
"""
        
        return plan
    
    def _get_plan_template(self, feedback_data: Dict, analysis: Dict) -> str:
        """Get implementation strategy template based on analysis"""
        
        templates = {
            'ui': """
This is a UI/UX improvement that will enhance user experience.
- Modify existing templates and CSS
- Ensure responsive design compatibility
- Test across different screen sizes
- Maintain consistent design language
            """,
            'stats': """
This is a statistics/dashboard feature enhancement.
- Implement new data aggregation logic
- Create or modify database queries
- Design appropriate visualization
- Ensure real-time data accuracy
            """,
            'database': """
This requires database schema or data management changes.
- Plan database migration strategy
- Ensure data integrity and backup
- Consider performance implications
- Test data migration thoroughly
            """,
            'api': """
This involves API or external service integration.
- Design API interface and error handling
- Implement authentication and security measures
- Add proper logging and monitoring
- Test edge cases and failure scenarios
            """,
            'content': """
This is a content or display modification.
- Update templates and static content
- Ensure Vietnamese language consistency
- Test content rendering across devices
- Validate accessibility compliance
            """,
            'feature': """
This is a new feature implementation.
- Design feature architecture and workflow
- Implement backend logic and database changes
- Create frontend interface and interactions
- Comprehensive testing and validation
            """
        }
        
        return templates.get(analysis['implementation_type'], templates['feature']).strip()
    
    def _generate_implementation_steps(self, feedback_data: Dict, analysis: Dict) -> str:
        """Generate specific implementation steps"""
        
        steps = []
        impl_type = analysis['implementation_type']
        
        if impl_type == 'ui':
            steps = [
                "1. 🎨 CSS/Style Changes:",
                "   - Modify base.html or specific template CSS",
                "   - Add new color schemes or layout adjustments",
                "   - Test responsive behavior",
                "",
                "2. 📱 Template Updates:",
                "   - Update HTML structure if needed",
                "   - Ensure Bootstrap compatibility",
                "   - Test across browsers",
                "",
                "3. ✅ Validation:",
                "   - Cross-browser testing",
                "   - Mobile responsiveness check",
                "   - Accessibility compliance"
            ]
        elif impl_type == 'stats':
            steps = [
                "1. 📊 Data Logic Implementation:",
                "   - Add new database queries in running_challenge_app.py",
                "   - Implement data aggregation functions",
                "   - Test query performance",
                "",
                "2. 🖥️ Frontend Display:",
                "   - Update weekly_results.html template",
                "   - Add new stats cards or charts",
                "   - Implement responsive design",
                "",
                "3. 🔄 Integration:",
                "   - Connect backend data to frontend",
                "   - Add loading states and error handling",
                "   - Test with real data"
            ]
        elif impl_type == 'database':
            steps = [
                "1. 📋 Schema Design:",
                "   - Plan new tables or column additions",
                "   - Design migration scripts",
                "   - Consider indexing and performance",
                "",
                "2. 🔄 Migration Implementation:",
                "   - Add migration code to init_db()",
                "   - Test migration on development environment",
                "   - Prepare rollback strategy",
                "",
                "3. 🔗 Application Integration:",
                "   - Update related queries and functions",
                "   - Modify templates to handle new data",
                "   - Test all affected features"
            ]
        else:
            steps = [
                "1. 🏗️ Backend Implementation:",
                "   - Add new routes in running_challenge_app.py",
                "   - Implement business logic",
                "   - Add error handling and logging",
                "",
                "2. 🎨 Frontend Development:",
                "   - Create or modify templates",
                "   - Add necessary JavaScript interactions",
                "   - Ensure responsive design",
                "",
                "3. 🔗 Integration & Testing:",
                "   - Connect frontend and backend",
                "   - Test user workflows",
                "   - Validate edge cases"
            ]
        
        return "\n".join(steps)
    
    def _generate_code_examples(self, feedback_data: Dict, analysis: Dict) -> str:
        """Generate relevant code examples"""
        
        impl_type = analysis['implementation_type']
        title = feedback_data['title']
        
        if impl_type == 'ui':
            return f"""
<!-- Example CSS addition to base.html -->
<style>
.new-feature-class {{
    /* Add styling based on feedback: {title} */
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 15px;
    padding: 1rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}}
</style>

<!-- Example HTML template update -->
<div class="new-feature-class">
    <!-- Content based on user feedback -->
</div>
"""
        elif impl_type == 'stats':
            return f"""
# Example backend query addition in running_challenge_app.py
@app.route('/weekly-results')
def weekly_results():
    # Existing code...
    
    # New stats calculation based on feedback: {title}
    cursor.execute('''
        SELECT 
            COUNT(*) as total_participants,
            AVG(total_distance) as avg_distance,
            MAX(total_distance) as max_distance
        FROM weekly_challenges 
        WHERE start_date = %s
    ''', (week_start,))
    new_stats = cursor.fetchone()
    
    return render_template('weekly_results.html', 
                         # existing parameters...
                         new_stats=new_stats)

<!-- Example template update in weekly_results.html -->
<div class="col-md-3">
    <div class="card stats-card border-0">
        <div class="card-body">
            <h5>New Stat</h5>
            <p>{{{{ new_stats.avg_distance | round(1) }}}} km</p>
        </div>
    </div>
</div>
"""
        else:
            return f"""
# Example implementation structure for: {title}

# 1. Backend route addition
@app.route('/new-feature')
def new_feature():
    try:
        # Implementation logic here
        return render_template('new_feature.html')
    except Exception as e:
        logger.error(f"Error in new feature: {{str(e)}}")
        flash('Đã xảy ra lỗi!', 'error')
        return redirect(url_for('home'))

# 2. Database changes (if needed)
cursor.execute('''
    ALTER TABLE weekly_challenges 
    ADD COLUMN new_field VARCHAR(255);
''')

# 3. Template creation
<!-- new_feature.html -->
{{% extends "base.html" %}}
{{% block content %}}
<div class="container">
    <!-- New feature content -->
</div>
{{% endblock %}}
"""
    
    def _generate_testing_plan(self, feedback_data: Dict, analysis: Dict) -> str:
        """Generate testing plan based on implementation type"""
        
        base_tests = [
            "✅ Unit Tests:",
            "   - Test individual functions",
            "   - Validate input/output",
            "   - Test error conditions",
            "",
            "✅ Integration Tests:",
            "   - Test database interactions",
            "   - Test API endpoints",
            "   - Test user workflows",
            "",
            "✅ UI/UX Tests:",
            "   - Cross-browser compatibility",
            "   - Mobile responsiveness",
            "   - Accessibility compliance",
            "",
            "✅ Performance Tests:",
            "   - Page load times",
            "   - Database query performance",
            "   - Memory usage impact"
        ]
        
        specific_tests = []
        impl_type = analysis['implementation_type']
        
        if impl_type == 'ui':
            specific_tests = [
                "🎨 UI-Specific Tests:",
                "   - Visual regression testing",
                "   - Color contrast validation",
                "   - Layout consistency check",
                "   - Animation performance"
            ]
        elif impl_type == 'stats':
            specific_tests = [
                "📊 Stats-Specific Tests:",
                "   - Data accuracy validation",
                "   - Calculation verification",
                "   - Edge case handling (zero data)",
                "   - Real-time update testing"
            ]
        elif impl_type == 'database':
            specific_tests = [
                "🗄️ Database-Specific Tests:",
                "   - Migration testing",
                "   - Data integrity validation",
                "   - Rollback procedure testing",
                "   - Performance impact assessment"
            ]
        
        all_tests = base_tests + [""] + specific_tests if specific_tests else base_tests
        return "\n".join(all_tests)
    
    def _generate_recommendations(self, feedback_data: Dict, analysis: Dict) -> str:
        """Generate implementation recommendations"""
        
        recommendations = []
        
        if analysis['complexity'] == 'high':
            recommendations.append("⚠️  High complexity - Consider breaking into smaller phases")
            recommendations.append("👥 Assign senior developer for implementation")
            recommendations.append("📋 Create detailed technical specification document")
        
        if analysis['implementation_type'] == 'database':
            recommendations.append("💾 Always backup database before schema changes")
            recommendations.append("🔄 Test migration on staging environment first")
            recommendations.append("⏰ Plan for potential downtime during deployment")
        
        if analysis['auto_implementable']:
            recommendations.append("🤖 This feature can be auto-implemented with AI assistance")
            recommendations.append("⚡ Consider immediate deployment after basic testing")
        else:
            recommendations.append("👨‍💻 Requires manual review and implementation")
            recommendations.append("🔍 Schedule technical review meeting before implementation")
        
        if feedback_data['priority'] == 'urgent':
            recommendations.append("🚨 High priority - Fast-track implementation")
            recommendations.append("📞 Notify stakeholders of implementation timeline")
        
        recommendations.append(f"📅 Estimated completion: {analysis['estimated_effort']}")
        recommendations.append("📈 Monitor user engagement after implementation")
        
        return "\n".join(f"- {rec}" for rec in recommendations)
    
    def save_generated_plan(self, feedback_id: int, plan: str) -> bool:
        """Save generated implementation plan to database"""
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if plan already exists
            cursor.execute('SELECT id FROM feature_generations WHERE feedback_id = %s', (feedback_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing plan
                cursor.execute('''
                    UPDATE feature_generations 
                    SET generated_code = %s, deployment_status = 'generated'
                    WHERE feedback_id = %s
                ''', (plan, feedback_id))
            else:
                # Create new plan
                cursor.execute('''
                    INSERT INTO feature_generations (feedback_id, generated_code, deployment_status)
                    VALUES (%s, %s, 'generated')
                ''', (feedback_id, plan))
            
            # Update feedback status
            cursor.execute('''
                UPDATE feedback 
                SET status = 'in_progress', implementation_status = 'planned', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (feedback_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Successfully saved implementation plan for feedback {feedback_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving implementation plan: {str(e)}")
            return False

if __name__ == "__main__":
    # Example usage
    generator = AIFeatureGenerator()
    
    # Test with sample feedback
    sample_feedback = {
        'title': 'Thêm biểu đồ tiến độ tuần',
        'description': 'Tôi muốn có biểu đồ hiển thị tiến độ chạy bộ của mình qua các tuần để dễ theo dõi',
        'feedback_type': 'suggestion',
        'priority': 'medium'
    }
    
    plan = generator.generate_implementation_plan(sample_feedback)
    print(plan)