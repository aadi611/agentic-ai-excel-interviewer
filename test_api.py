import requests
import json

# Test the API directly
def test_evaluation_system():
    print("🧪 Testing Excel Assessment API...")
    
    # Start a new session
    session_response = requests.post("http://127.0.0.1:8000/api/session/create")
    print(f"Session creation: {session_response.status_code}")
    
    if session_response.status_code == 200:
        session_data = session_response.json()
        session_id = session_data.get('session_id')
        print(f"Session ID: {session_id}")
        
        # Start the interview
        start_response = requests.post(f"http://127.0.0.1:8000/api/session/{session_id}/start")
        print(f"Interview start: {start_response.status_code}")
        
        if start_response.status_code == 200:
            start_data = start_response.json()
            print(f"Question: {start_data.get('question', 'N/A')}")
            print(f"Start data keys: {list(start_data.keys())}")
            
            # Submit an answer
            answer_data = {
                "session_id": session_id,
                "message": "AutoSum is used to automatically calculate the sum of a range of cells. You can access it by clicking the AutoSum button in the Home tab or by pressing Alt + = ."
            }
            
            answer_response = requests.post(
                f"http://127.0.0.1:8000/api/session/{session_id}/respond",
                json=answer_data
            )
            print(f"Answer submission: {answer_response.status_code}")
            
            if answer_response.status_code == 200:
                evaluation_data = answer_response.json()
                print("\n🎯 Full Response Data:")
                print(f"Keys: {list(evaluation_data.keys())}")
                for key, value in evaluation_data.items():
                    if isinstance(value, dict):
                        print(f"{key}: {list(value.keys())}")
                    else:
                        print(f"{key}: {str(value)[:100]}...")
                
                print("\n🎯 ICE Scorecard Data:")
                if 'ice_scorecard' in evaluation_data:
                    ice = evaluation_data['ice_scorecard']
                    print(f"Impact: {ice.get('impact_score', 'N/A')}")
                    print(f"Confidence: {ice.get('confidence_score', 'N/A')}")
                    print(f"Ease: {ice.get('ease_score', 'N/A')}")
                    print(f"Composite Score: {ice.get('composite_score', 'N/A')}")
                elif 'evaluation_result' in evaluation_data:
                    eval_result = evaluation_data['evaluation_result']
                    print(f"✅ Found evaluation result!")
                    print(f"Impact: {eval_result.get('impact_score', 'N/A')}")
                    print(f"Confidence: {eval_result.get('confidence_score', 'N/A')}")
                    print(f"Ease: {eval_result.get('ease_score', 'N/A')}")
                    print(f"Composite Score: {eval_result.get('ice_composite_score', 'N/A')}")
                elif 'candidate_insights' in evaluation_data:
                    insights = evaluation_data['candidate_insights']
                    print(f"Checking candidate_insights: {type(insights)}")
                    if isinstance(insights, dict):
                        print(f"Insights keys: {list(insights.keys())}")
                else:
                    print("❌ No ICE scorecard data found!")
                    print("Raw response keys:", list(evaluation_data.keys()))
                    
                # Try submitting another answer to get to questioning phase
                print("\n🔄 Submitting second answer...")
                answer_data2 = {
                    "session_id": session_id,
                    "message": "I use Excel daily for data analysis, creating pivot tables, and financial modeling. I'm comfortable with VLOOKUP, INDEX-MATCH, and conditional formatting."
                }
                
                answer_response2 = requests.post(
                    f"http://127.0.0.1:8000/api/session/{session_id}/respond",
                    json=answer_data2
                )
                
                if answer_response2.status_code == 200:
                    evaluation_data2 = answer_response2.json()
                    print(f"Second response keys: {list(evaluation_data2.keys())}")
                    
                    if 'ice_scorecard' in evaluation_data2:
                        ice = evaluation_data2['ice_scorecard']
                        print(f"✅ Found ICE data!")
                        print(f"Impact: {ice.get('impact_score', 'N/A')}")
                        print(f"Confidence: {ice.get('confidence_score', 'N/A')}")
                        print(f"Ease: {ice.get('ease_score', 'N/A')}")
                        print(f"Composite Score: {ice.get('composite_score', 'N/A')}")
                    elif 'evaluation_result' in evaluation_data2:
                        eval_result = evaluation_data2['evaluation_result']
                        print(f"✅ Found evaluation result!")
                        print(f"Impact: {eval_result.get('impact_score', 'N/A')}")
                        print(f"Confidence: {eval_result.get('confidence_score', 'N/A')}")
                        print(f"Ease: {eval_result.get('ease_score', 'N/A')}")
                        print(f"Composite Score: {eval_result.get('ice_composite_score', 'N/A')}")
                    else:
                        print("❌ Still no ICE scorecard data in second response")
                else:
                    print(f"❌ Second answer submission failed: {answer_response2.status_code}")
            else:
                print(f"❌ Answer submission failed: {answer_response.text}")
        else:
            print(f"❌ Interview start failed: {start_response.text}")
    else:
        print(f"❌ Session creation failed: {session_response.text}")

if __name__ == "__main__":
    test_evaluation_system()