import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [mockups, setMockups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState('upload'); // upload, processing, results

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setImagePreview(URL.createObjectURL(selectedFile));
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setStep('processing');

    try {
      // 1. Analyze Image
      const formData = new FormData();
      formData.append('file', file);

      const analysisResponse = await axios.post('http://localhost:8000/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysis(analysisResponse.data);

      // 2. Generate Mockups
      // Convert file to base64 for the generation request
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onloadend = async () => {
        const base64Image = reader.result;

        const generationRequest = {
            garment_type: analysisResponse.data.garment_type,
            dominant_color_hex: analysisResponse.data.dominant_color_hex,
            image_base64: base64Image
        };

        const generationResponse = await axios.post('http://localhost:8000/generate', generationRequest);
        setMockups(generationResponse.data);
        setLoading(false);
        setStep('results');
      };

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
      link.target = "_blank"; // Important for static file downloads sometimes
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
            <div className="upload-box">
              <input
                type="file"
                id="file-upload"
                accept="image/*"
                onChange={handleFileChange}
                className="file-input"
              />
              <label htmlFor="file-upload" className="file-label">
                {imagePreview ? (
                  <img src={imagePreview} alt="Preview" className="preview-image" />
                ) : (
                  <div className="upload-placeholder">
                    <span>+</span>
                    <p>Upload Product Image</p>
                  </div>
                )}
              </label>
            </div>
            {file && (
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
