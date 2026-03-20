import React, { useState, useEffect } from "react";
import { FaPlus, FaExternalLinkAlt, FaEdit, FaTrash } from "react-icons/fa";
import CreateResourceModal from "./CreateResorceModal";
import { CiImageOff } from "react-icons/ci";
import "./GuidesPage.css";

const GuidesPage = () => {
  const [resources, setResources] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState("All");

  // Cargar recursos desde localStorage al iniciar
  useEffect(() => {
    const savedResources = localStorage.getItem("developerResources");
    if (savedResources) {
      setResources(JSON.parse(savedResources));
    } else {
      // Recursos de ejemplo
      setResources([
        {
          id: 1,
          title: "React Documentation",
          description: "Official React documentation with guides and API reference",
          link: "https://react.dev",
          category: "Frontend",
          image: "https://react.dev/images/home/conf2021/cover.svg",
          createdAt: "2025-11-15"
        },
        {
          id: 2,
          title: "LangChain Docs",
          description: "Build context-aware AI applications with LangChain",
          link: "https://python.langchain.com",
          category: "AI/ML",
          image: "",
          owner: "",
          createdAt: "2025-11-14"
        },
        {
          id: 3,
          title: "Tailwind CSS",
          description: "Utility-first CSS framework for rapid UI development",
          link: "https://tailwindcss.com",
          category: "CSS",
          createdAt: "2025-11-13"
        }
      ]);
    }
  }, []);

  // Guardar recursos en localStorage cuando cambien
  useEffect(() => {
    if (resources.length > 0) {
      localStorage.setItem("developerResources", JSON.stringify(resources));
    }
  }, [resources]);

  // Agregar nuevo recurso
  const handleAddResource = (newResource) => {
    const resource = {
      ...newResource,
      id: Date.now(),
      createdAt: new Date().toISOString().split('T')[0]
    };
    setResources([resource, ...resources]);
    setIsModalOpen(false);
  };

  // Eliminar recurso
  const handleDeleteResource = (id) => {
    if (window.confirm("Are you sure you want to delete this resource?")) {
      setResources(resources.filter(r => r.id !== id));
    }
  };

  // Filtrar por categoría
  const categories = ["All", ...new Set(resources.map(r => r.category))];
  const filteredResources = selectedCategory === "All" 
    ? resources 
    : resources.filter(r => r.category === selectedCategory);

  return (
  <div className="resources-page-container">
    {/* Header */}
    <div className="resources-header">
      <div className="resources-header-content">
        <h1 className="resources-main-title">Developer Resources</h1>
        <p className="resources-subtitle">
          Curated collection of tools, docs, and guides for developers
        </p>
      </div>
      <button 
        className="resources-btn-create"
        onClick={() => setIsModalOpen(true)}
      >
        <FaPlus /> Create Resource
      </button>
    </div>

    {/* Filtros por categoría */}
    <div className="resources-category-filters">
      {categories.map(cat => (
        <button
          key={cat}
          className={`resources-category-btn ${selectedCategory === cat ? 'active' : ''}`}
          onClick={() => setSelectedCategory(cat)}
        >
          {cat}
        </button>
      ))}
    </div>

    {/* Grid de recursos */}
    <div className="resources-grid-container">
      {filteredResources.length === 0 ? (
        <div className="resources-empty-state">
          <p>No resources found. Create your first one!</p>
        </div>
      ) : (
        filteredResources.map(resource => (
          <div key={resource.id} className="resources-card">
            {/* Imagen */}
            <div className="resources-card-image">
                {resource.image && resource.image.trim() !== "" ? (
                    <img 
                    src={resource.image} 
                    alt={resource.title}
                    onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentElement.classList.add('no-image');
                    }}
                    />
                ) : (
                    <div className="no-image-placeholder">
                    <CiImageOff />
                    <span>No Image</span>
                    </div>
                )}
                <div className="resources-category-badge">{resource.category}</div>
                </div>

            {/* Contenido */}
            <div className="resources-card-content">
              <h3 className="resources-card-title">{resource.title}</h3>
              <p className="resources-card-description">{resource.description}</p>
              
              {/* Footer del card */}
              <div className="resources-card-footer">
                <div className="resources-card-meta">
                    {resource.owner && (
                    <span className="resources-card-owner">
                        👤 {resource.owner}
                    </span>
                    )}
                    <span className="resources-card-date">{resource.createdAt}</span>
                </div>
                <div className="resources-card-actions">
                  <a 
                    href={resource.link} 
                    target="_blank" 
                    rel="noreferrer"
                    className="resources-btn-action resources-btn-visit"
                    title="Visit"
                  >
                    <FaExternalLinkAlt />
                  </a>
                  <button 
                    className="resources-btn-action resources-btn-delete"
                    onClick={() => handleDeleteResource(resource.id)}
                    title="Delete"
                  >
                    <FaTrash />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))
      )}
    </div>

    {/* Modal */}
    {isModalOpen && (
      <CreateResourceModal
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleAddResource}
      />
    )}
  </div>
);
};
export default GuidesPage;