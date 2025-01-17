"use client";
import { useState } from 'react';

const SimpleFileUpload = () => {
  const [file, setFile] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setPrediction(null);
    setError(null);
  };
  console.log(file);

  const handlePredict = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch("/predict", {
        method: 'POST',
        body: formData,
      });
      console.log("response");
      console.log(response);

      if (!response.ok) {
        throw new Error('Prediction failed');
      }

      const data = await response.json();
      setPrediction(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-8 p-6 border rounded-lg shadow-sm">
      <h2 className="text-xl font-bold mb-4">File Upload & Predict</h2>
      
      <div className="space-y-4">
        <div>
          <input
            type="file"
            onChange={handleFileChange}
            className="mb-4"
          />
        </div>

        {file && (
          <div className="text-sm text-gray-500">
            Selected file: {file.name}
          </div>
        )}

        <button
          onClick={handlePredict}
          disabled={!file || loading}
          className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? 'Processing...' : 'Predict'}
        </button>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {prediction && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium mb-2">Prediction Result:</h3>
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(prediction, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimpleFileUpload;