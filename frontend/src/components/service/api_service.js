import axios from 'axios';


const REACT_APP = process.env.REACT_APP_URL; // Localhost:5000 o la URL de tu backend en producción
//const REACT_APP_URL = process.env.REACT_APP_URL_AZURE_PROMPT; // Azure Functions Nube


const onPrompt = async (promptText) => {
    try {
      const response = await axios.post(`${REACT_APP}/api/search/prompt`, { 
        prompt: promptText
      },{
        headers: {
          'Content-Type': 'application/json; charset=utf-8"',
        }
      });
      return response.data; // Asegúrate de que esto coincida con la estructura de tu backend
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Error al introducir el prompt');
    }
  };
  
  export default onPrompt;