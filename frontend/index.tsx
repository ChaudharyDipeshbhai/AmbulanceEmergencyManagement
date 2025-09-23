import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';

// Point to the new Python FastAPI backend URL
const API_BASE_URL = 'http://localhost:8000';

const triageData = {
  "questions": {
    "1_Fainted_Unconscious": {
      "question": "Is patient awake?",
      "options": {
        "Yes": { "level": 1 },
        "No": {
          "next": {
            "question": "Is patient breathing?",
            "options": {
              "Yes": {
                "next": {
                  "question": "How long unconscious?",
                  "options": {
                    "< 2 minutes": { "level": 2 },
                    "2-5 minutes": { "level": 2 },
                    "> 5 minutes": { "level": 3 }
                  }
                }
              },
              "No": { "level": 4 }
            }
          }
        }
      }
    },
    "2_ChestPain_Breathing": {
      "question": "Was pain sudden or severe?",
      "options": {
        "No": { "level": 2 },
        "Yes": {
          "next": {
            "question": "Sweating or vomiting?",
            "options": {
              "No": { "level": 2 },
              "Yes": { "level": 3 }
            }
          }
        }
      }
    },
    "3_Accident": {
      "question": "How many people injured?",
      "options": {
        "One": {
          "next": {
            "question": "Is person awake?",
            "options": {
              "Yes": {
                "next": {
                  "question": "Any major bleeding/fracture?",
                  "options": {
                    "No": { "level": 1 },
                    "Yes": { "level": 2 }
                  }
                }
              },
              "No": { "level": 3 }
            }
          }
        },
        "Multiple": { "level": 3 },
        "Deaths": { "level": 4 }
      }
    },
    "4_Injury_Fall": {
      "question": "Is patient conscious?",
      "options": {
        "Yes": {
          "next": {
            "question": "Bleeding or fracture?",
            "options": {
              "No": { "level": 1 },
              "Yes": { "level": 2 }
            }
          }
        },
        "No": { "level": 3 }
      }
    },
    "5_Sickness": {
      "question": "What is the illness?",
      "options": {
        "Mild symptoms (fever, cold)": { "level": 1 },
        "Severe symptoms (chest pain, high fever)": { "level": 2 }
      }
    },
    "6_Pregnancy": {
      "question": "Contraction pain?",
      "options": {
        "No": { "level": 1 },
        "Yes": {
          "next": {
            "question": "Bleeding or water broken?",
            "options": {
              "No": { "level": 2 },
              "Water broken": { "level": 2 },
              "Bleeding": { "level": 3 }
            }
          }
        }
      }
    },
    "7_Poisoning_Bite": {
      "question": "Is patient conscious?",
      "options": {
        "Yes": {
          "next": {
            "question": "Swelling or breathing issues?",
            "options": {
              "No": { "level": 2 },
              "Yes": { "level": 3 }
            }
          }
        },
        "No": { "level": 4 }
      }
    },
    "8_Fire": {
      "question": "How large is the fire?",
      "options": {
        "Small, no injuries": { "level": 1 },
        "Medium, injuries possible": { "level": 2 },
        "Large, people trapped": { "level": 4 }
      }
    }
  }
};


type TriageHistory = { question: string; answer: string };
type QuestionNode = {
    question: string;
    options: {
        [key: string]: {
            level?: number;
            next?: QuestionNode;
        };
    };
};


const App = () => {
    const [currentScenario, setCurrentScenario] = useState<string | null>(null);
    const [currentQuestion, setCurrentQuestion] = useState<QuestionNode | null>(null);
    const [history, setHistory] = useState<TriageHistory[]>([]);
    const [level, setLevel] = useState<number | null>(null);
    const [explanation, setExplanation] = useState<string>('');
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [mobileNumber, setMobileNumber] = useState<string>('');
    const [latitude, setLatitude] = useState<string>('');
    const [longitude, setLongitude] = useState<string>('');
    
    // State to track if caller data was fetched automatically
    const [dataFetchStatus, setDataFetchStatus] = useState<'loading' | 'success' | 'failed'>('loading');

    // useEffect to fetch data from the backend when the app loads
    useEffect(() => {
        const fetchCallerData = async () => {
            setDataFetchStatus('loading');
            try {
                // Make a real API call to our new backend server
                const response = await fetch(`${API_BASE_URL}/api/caller-info`);
                if (!response.ok) {
                    // If the server responds with an error, throw it to the catch block
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                const data = await response.json();
                setMobileNumber(data.caller_id);
                setLatitude(data.location.lat.toString());
                setLongitude(data.location.lng.toString());
                setDataFetchStatus('success');
            } catch (error) {
                console.error("Failed to fetch caller data from backend:", error);
                setDataFetchStatus('failed');
            }
        };

        fetchCallerData();
    }, []); // The empty dependency array [] ensures this effect runs only once on mount

    const formatScenarioName = (key: string) => {
        return key.split('_').slice(1).join(' / ');
    }
    
    // Function to format and send the final data to the backend
    const sendDataToBackend = async (finalLevel: number) => {
        const payload = {
            caller_id: mobileNumber,
            location: {
                lat: parseFloat(latitude) || null,
                lng: parseFloat(longitude) || null,
            },
            emergency_level: finalLevel
        };

        try {
            const response = await fetch(`${API_BASE_URL}/api/triage-report`, { 
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload) 
            });

            if (!response.ok) {
                throw new Error(`Backend responded with status: ${response.status}`);
            }

            const result = await response.json();
            console.log("Backend response:", result);

        } catch (error) {
            console.error("Error sending data to backend:", error);
            // Optionally, show an error message to the user in the UI
        }
    };

    const handleScenarioSelect = (scenarioKey: string) => {
        const scenarioData = triageData.questions[scenarioKey];
        setCurrentScenario(formatScenarioName(scenarioKey));
        setCurrentQuestion(scenarioData);
        setHistory([]);
        setLevel(null);
        setExplanation('');
    };

    const handleOptionSelect = async (option: string) => {
        if (!currentQuestion || !currentScenario) return;

        const newHistory = [...history, { question: currentQuestion.question, answer: option }];
        setHistory(newHistory);

        const result = currentQuestion.options[option];
        if (result.next) {
            setCurrentQuestion(result.next);
        } else if (result.level) {
            const finalLevel = result.level;
            setLevel(finalLevel);
            
            // Call the function to send data to the backend
            sendDataToBackend(finalLevel);
            
            // Generate a simple local explanation instead of calling an API
            const finalAnswer = newHistory[newHistory.length - 1];
            const explanationText = `Severity level ${finalLevel} was assigned based on the answer: "${finalAnswer.answer}".`;
            setExplanation(explanationText);
        }
    };
    
    const handleManualOverride = async (overrideLevel: number) => {
        setLevel(overrideLevel);
        setCurrentScenario(`Manual Override to Level ${overrideLevel}`);
        
        // Call the function to send data to the backend
        sendDataToBackend(overrideLevel);

        // Generate a simple local explanation for the manual override
        setExplanation(`The operator has manually set the emergency severity level to ${overrideLevel}.`);
    };

    const resetTriage = () => {
        setCurrentScenario(null);
        setCurrentQuestion(null);
        setHistory([]);
        setLevel(null);
        setExplanation('');
        setIsLoading(false);
        // Do not reset caller info, as a new triage might be for the same caller
    };
    
    // Helper to render the status of the automatic data fetch
    const renderFetchStatus = () => {
        switch (dataFetchStatus) {
            case 'loading':
                return <p className="fetch-status loading">Connecting to server to fetch caller details...</p>;
            case 'success':
                return <p className="fetch-status success">✓ Caller details fetched automatically.</p>;
            case 'failed':
                return <p className="fetch-status failed">! Could not fetch details. Please enter manually.</p>;
            default:
                return null;
        }
    };

    const renderTriageFlow = () => {
        if (level !== null) {
            return (
                <div className={`result-view severity-${level}`}>
                    <h2>Final Emergency Severity Level: {level}</h2>
                    <p>{explanation}</p>
                    <button onClick={resetTriage} className="submit-btn">Start New Triage</button>
                </div>
            );
        }

        if (currentQuestion) {
            return (
                <div className="form-group">
                    <h2 className="form-label" id="question-label">{currentQuestion.question}</h2>
                    <div className="options-group" role="group" aria-labelledby="question-label">
                        {Object.keys(currentQuestion.options).map(option => (
                            <button key={option} onClick={() => handleOptionSelect(option)} className="option-btn">
                                {option}
                            </button>
                        ))}
                    </div>
                </div>
            );
        }

        return (
            <>
                <div className="form-group">
                    <h2 className="form-label" id="scenario-label">What is the emergency scenario?</h2>
                    <div className="options-group" role="group" aria-labelledby="scenario-label">
                        {Object.keys(triageData.questions).map(scenarioKey => (
                            <button key={scenarioKey} onClick={() => handleScenarioSelect(scenarioKey)} className="option-btn">
                                {formatScenarioName(scenarioKey)}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="form-group">
                     <h3 className="sub-label">Or, select a manual override:</h3>
                    <div className="options-group manual-override-group">
                        <button onClick={() => handleManualOverride(4)} className="option-btn override-btn-4">Level 4 (Highest)</button>
                        <button onClick={() => handleManualOverride(3)} className="option-btn override-btn-3">Level 3 (High)</button>
                        <button onClick={() => handleManualOverride(2)} className="option-btn override-btn-2">Level 2 (Medium)</button>
                        <button onClick={() => handleManualOverride(1)} className="option-btn override-btn-1">Level 1 (Low)</button>
                    </div>
                </div>
            </>
        );
    };

    return (
        <main className="container">
            <h1>Ambulance Dispatch System</h1>

            {/* Caller info section now has dynamic rendering based on fetch status */}
            {!currentQuestion && level === null && (
                 <div className="caller-info-container">
                    {renderFetchStatus()}
                    <div className="caller-info-group">
                        <div className="input-group">
                            <label htmlFor="mobileNumber" className="input-label">Mobile Number</label>
                            <input
                                type="tel"
                                id="mobileNumber"
                                value={mobileNumber}
                                onChange={(e) => setMobileNumber(e.target.value)}
                                placeholder="Enter mobile number"
                                className="input-field"
                                aria-label="Mobile Number"
                                readOnly={dataFetchStatus === 'success'}
                            />
                        </div>
                        <div className="location-inputs-container">
                            <div className="input-group">
                                <label htmlFor="latitude" className="input-label">Latitude</label>
                                <input
                                    type="text"
                                    id="latitude"
                                    value={latitude}
                                    onChange={(e) => setLatitude(e.target.value)}
                                    placeholder="e.g., 40.7128"
                                    className="input-field"
                                    aria-label="Latitude"
                                    readOnly={dataFetchStatus === 'success'}
                                />
                            </div>
                            <div className="input-group">
                                <label htmlFor="longitude" className="input-label">Longitude</label>
                                <input
                                    type="text"
                                    id="longitude"
                                    value={longitude}
                                    onChange={(e) => setLongitude(e.target.value)}
                                    placeholder="e.g., -74.0060"
                                    className="input-field"
                                    aria-label="Longitude"
                                    readOnly={dataFetchStatus === 'success'}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            )}
            
            {renderTriageFlow()}
        </main>
    );
};

const container = document.getElementById('root');
if (container) {
    const root = createRoot(container);
    root.render(<App />);
}
