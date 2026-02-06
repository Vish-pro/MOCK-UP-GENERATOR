import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [frontFile, setFrontFile] = useState(null);
  const [backFile, setBackFile] = useState(null);
  const [frontPreview, setFrontPreview] = useState(null);
  const [backPreview, setBackPreview] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [mockups, setMockups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState('upload'); // upload, processing, results

  const handleFileChange = (e, side) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (side === 'front') {
        setFrontFile(selectedFile);
        setFrontPreview(URL.createObjectURL(selectedFile));
      } else {
        setBackFile(selectedFile);
        setBackPreview(URL.createObjectURL(selectedFile));
      }
    }
  };

  const handleUpload = async () => {
    if (!frontFile) {
      alert("Please upload at least the front image.");
      return;
    }

    setLoading(true);
    setStep('processing');

    try {
      // 1. Analyze Front Image
      const formData = new FormData();
      formData.append('file', frontFile);

      const analysisResponse = await axios.post('/api/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setAnalysis(analysisResponse.data);

      // 2. Read images as base64
      const readFileAsBase64 = (file) => {
        return new Promise((resolve) => {
          if (!file) {
            resolve(null);
            return;
          }
          const reader = new FileReader();
          reader.readAsDataURL(file);
          reader.onloadend = () => resolve(reader.result);
        });
      };

      const frontBase64 = await readFileAsBase64(frontFile);
      const backBase64 = await readFileAsBase64(backFile);

      // 3. Generate Mockups
      const generationRequest = {
        garment_type: analysisResponse.data.garment_type,
        dominant_color_hex: analysisResponse.data.dominant_color_hex,
        front_image_base64: frontBase64,
        back_image_base64: backBase64
      };

      const generationResponse = await axios.post('/api/generate', generationRequest);
      setMockups(generationResponse.data.mockups);
      if (generationResponse.data.ai_analysis) {
        console.log("Gemini Suggestions:", generationResponse.data.ai_analysis);
        // Optionally store analysis in state to display to user
        setAnalysis(prev => ({ ...prev, ai_analysis: generationResponse.data.ai_analysis }));
      }
      setLoading(false);
      setStep('results');

    } catch (error) {
      console.error("Error processing image:", error);
      alert("An error occurred. Please try again.");
      setLoading(false);
      setStep('upload');
    }
  };

  const downloadAll = () => {
    mockups.forEach((mockup, index) => {
      const link = document.createElement('a');
      link.href = mockup.image_base64;
      link.download = `mockup_${mockup.category.substring(0, 10)}_${mockup.view_name.replace(" ", "_")}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>One-Click E-Commerce Studio</h1>
        <p>Automated 4K Asset Generation</p>
      </header>

      <main className="app-main">
        {step === 'upload' && (
          <div className="upload-section">
            <div className="upload-container-row">
              <div className="upload-group">
                <h3>Front View</h3>
                <div className="upload-box">
                  <input
                    type="file"
                    id="front-upload"
                    accept="image/*"
                    onChange={(e) => handleFileChange(e, 'front')}
                    className="file-input"
                  />
                  <label htmlFor="front-upload" className="file-label">
                    {frontPreview ? (
                      <img src={frontPreview} alt="Front Preview" className="preview-image" />
                    ) : (
                      <div className="upload-placeholder">
                        <span>+</span>
                        <p>Upload Front</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              <div className="upload-group">
                <h3>Back View</h3>
                <div className="upload-box">
                  <input
                    type="file"
                    id="back-upload"
                    accept="image/*"
                    onChange={(e) => handleFileChange(e, 'back')}
                    className="file-input"
                  />
                  <label htmlFor="back-upload" className="file-label">
                    {backPreview ? (
                      <img src={backPreview} alt="Back Preview" className="preview-image" />
                    ) : (
                      <div className="upload-placeholder">
                        <span>+</span>
                        <p>Upload Back (Optional)</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>
            </div>
            {frontFile && (
              <button className="primary-button" onClick={handleUpload}>
                Start Studio Workflow
              </button>
            )}
          </div>
        )}

        {step === 'processing' && (
          <div className="processing-section">
            <div className="spinner"></div>
            <h2>Processing your asset...</h2>
            <p>Analyzing Garment Type & Color...</p>
            <p>Generating 12 High-Fidelity 4K Mockups...</p>
          </div>
        )}

        {step === 'results' && analysis && (
          <div className="results-section">
            <div className="analysis-summary">
              <div className="info-card">
                <h3>Detected Garment</h3>
                <p>{analysis.garment_type}</p>
              </div>
              <div className="info-card">
                <h3>Dominant Color</h3>
                <div className="color-swatch-container">
                  <div
                    className="color-swatch"
                    style={{ backgroundColor: analysis.dominant_color_hex }}
                  ></div>
                  <span>{analysis.dominant_color_hex}</span>
                </div>
              </div>
              {analysis.ai_analysis && (
                <div className="info-card wide ai-card">
                  <h3>AI Insights & Styling</h3>
                  <p className="ai-text">{analysis.ai_analysis}</p>
                </div>
              )}
              <button className="secondary-button" onClick={() => setStep('upload')}>Start New</button>
              <button className="primary-button" onClick={downloadAll}>Download All 4K Assets</button>
            </div>

            <div className="gallery">
              <h2>Category A: With Humans (Faceless)</h2>
              <div className="image-grid">
                {mockups.filter(m => m.category.includes("Category A")).map((mockup, idx) => (
                  <div key={idx} className="mockup-card">
                    <img src={mockup.image_base64} alt={mockup.view_name} />
                    <p>{mockup.view_name}</p>
                  </div>
                ))}
              </div>

              <h2>Category B: Without Humans (Ghost Mannequin)</h2>
              <div className="image-grid">
                {mockups.filter(m => m.category.includes("Category B")).map((mockup, idx) => (
                  <div key={idx} className="mockup-card">
                    <img src={mockup.image_base64} alt={mockup.view_name} />
                    <p>{mockup.view_name}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
