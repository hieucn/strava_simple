#!/usr/bin/env python3
"""
Test script for the feedback system
Validates the feedback system functionality without requiring Flask to run
"""

import sys
import os

def test_imports():
    """Test that all necessary modules can be imported"""
    try:
        # Test AI feature generator
        from ai_feature_generator import AIFeatureGenerator
        print("✅ AI Feature Generator imported successfully")
        
        # Test Docker manager
        from docker_manager import DockerManager
        print("✅ Docker Manager imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_ai_generator():
    """Test AI feature generator functionality"""
    try:
        from ai_feature_generator import AIFeatureGenerator
        
        generator = AIFeatureGenerator()
        
        # Test with sample feedback
        sample_feedback = {
            'title': 'Thêm biểu đồ tiến độ hàng tuần',
            'description': 'Tôi muốn có biểu đồ hiển thị tiến độ chạy bộ của mình qua các tuần để dễ theo dõi sự cải thiện',
            'feedback_type': 'suggestion',
            'priority': 'medium'
        }
        
        # Test analysis
        analysis = generator.analyze_feedback(sample_feedback)
        print(f"✅ Feedback analysis: {analysis}")
        
        # Test plan generation
        plan = generator.generate_implementation_plan(sample_feedback)
        print("✅ Implementation plan generated successfully")
        print(f"   Plan length: {len(plan)} characters")
        
        return True
    except Exception as e:
        print(f"❌ AI generator test failed: {e}")
        return False

def test_docker_manager():
    """Test Docker manager functionality"""
    try:
        from docker_manager import DockerManager
        
        manager = DockerManager()
        
        # Test container finding (will fail if Docker not available, but shouldn't crash)
        try:
            container = manager.find_app_container()
            if container:
                print(f"✅ Found container: {container}")
            else:
                print("⚠️  No container found (expected if not running in Docker)")
        except Exception as e:
            print(f"⚠️  Docker not available: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Docker manager test failed: {e}")
        return False

def test_templates():
    """Test that template files exist and are readable"""
    templates = [
        'templates/feedback.html',
        'templates/admin_feedback.html'
    ]
    
    success = True
    for template in templates:
        try:
            with open(template, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) > 0:
                    print(f"✅ Template {template} is readable ({len(content)} chars)")
                else:
                    print(f"❌ Template {template} is empty")
                    success = False
        except Exception as e:
            print(f"❌ Template {template} error: {e}")
            success = False
    
    return success

def test_deployment_script():
    """Test that deployment script exists and is executable"""
    try:
        import stat
        
        script_path = 'deploy.sh'
        if os.path.exists(script_path):
            file_stat = os.stat(script_path)
            if file_stat.st_mode & stat.S_IEXEC:
                print("✅ Deployment script is executable")
                return True
            else:
                print("⚠️  Deployment script exists but is not executable")
                return False
        else:
            print("❌ Deployment script not found")
            return False
    except Exception as e:
        print(f"❌ Deployment script test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Feedback System Components")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("AI Feature Generator", test_ai_generator),
        ("Docker Manager", test_docker_manager),
        ("Template Files", test_templates),
        ("Deployment Script", test_deployment_script)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Feedback system is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())