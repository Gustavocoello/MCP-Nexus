import axios from 'axios';


const REACT_APP = process.env.REACT_APP_URL;


const onPrompt = async (promptText) => {
    try {
      const response = await axios.post(`${REACT_APP}/api/search/prompt`, { 
        prompt: promptText
      });
      return response.data; // Asegúrate de que esto coincida con la estructura de tu backend
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Error al introducir el prompt');
    }
  };
  
  export default onPrompt;