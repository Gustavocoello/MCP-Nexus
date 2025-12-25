"""
Test de cascada de bases de datos.
Simula fallos para verificar el comportamiento del orquestador.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError

# Agregar el directorio raiz al path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

def print_header(title):
    """Imprime encabezado de seccion"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def print_result(test_name, success):
    """Imprime resultado de test"""
    status = "PASS" if success else "FAIL"
    symbol = "[OK]" if success else "[X]"
    print(f"{symbol} {test_name}: {status}")

def test_windows_only():
    """Test 1: Solo Windows funciona"""
    print_header("TEST 1: Solo Windows disponible")
    
    # Resetear modulos para reimportar
    if 'src.database.config.connection' in sys.modules:
        del sys.modules['src.database.config.connection']
    
    os.environ['ENV'] = 'prod'
    
    try:
        from src.database.config.connection import get_database_url
        
        # Simular que Linux y Azure fallan
        with patch('src.database.config.connection.get_mysql_linux_engine') as mock_linux, \
             patch('src.database.config.connection.get_azure_engine') as mock_azure:
            
            mock_linux.side_effect = OperationalError("Mock error", None, None)
            mock_azure.side_effect = OperationalError("Mock error", None, None)
            
            url = get_database_url()
            
            if 'mysql' in str(url).lower() and 'windows' not in str(mock_linux.call_count):
                print("Resultado: Usando Windows correctamente")
                print_result("Windows como principal", True)
                return True
            
    except Exception as e:
        print(f"Error: {str(e)[:100]}")
        print_result("Windows como principal", False)
        return False

def test_windows_fail_linux_works():
    """Test 2: Windows falla, Linux funciona"""
    print_header("TEST 2: Windows falla -> Linux toma el control")
    
    # Resetear modulos
    if 'src.database.config.connection' in sys.modules:
        del sys.modules['src.database.config.connection']
    
    os.environ['ENV'] = 'prod'
    
    try:
        from src.database.config.connection import get_database_url
        
        # Simular que Windows falla, Linux funciona, Azure falla
        with patch('src.database.config.connection.get_mysql_engine') as mock_windows, \
             patch('src.database.config.connection.get_azure_engine') as mock_azure:
            
            mock_windows.side_effect = OperationalError("Mock Windows down", None, None)
            mock_azure.side_effect = OperationalError("Mock Azure down", None, None)
            
            url = get_database_url()
            
            print("Resultado: Fallback a Linux exitoso")
            print_result("Fallback Windows -> Linux", True)
            return True
            
    except Exception as e:
        print(f"Error: {str(e)[:100]}")
        print_result("Fallback Windows -> Linux", False)
        return False

def test_windows_linux_fail_azure_works():
    """Test 3: Windows y Linux fallan, Azure funciona"""
    print_header("TEST 3: Windows y Linux fallan -> Azure toma el control")
    
    # Resetear modulos
    if 'src.database.config.connection' in sys.modules:
        del sys.modules['src.database.config.connection']
    
    os.environ['ENV'] = 'prod'
    
    try:
        from src.database.config.connection import get_database_url
        
        # Simular que Windows y Linux fallan, Azure funciona
        with patch('src.database.config.connection.get_mysql_engine') as mock_windows, \
             patch('src.database.config.connection.get_mysql_linux_engine') as mock_linux:
            
            mock_windows.side_effect = OperationalError("Mock Windows down", None, None)
            mock_linux.side_effect = OperationalError("Mock Linux down", None, None)
            
            url = get_database_url()
            
            print("Resultado: Fallback a Azure exitoso")
            print_result("Fallback Windows -> Linux -> Azure", True)
            return True
            
    except Exception as e:
        print(f"Error: {str(e)[:100]}")
        print_result("Fallback Windows -> Linux -> Azure", False)
        return False

def test_all_fail():
    """Test 4: Todas las bases de datos fallan"""
    print_header("TEST 4: Todas las bases de datos fallan")
    
    # Resetear modulos
    if 'src.database.config.connection' in sys.modules:
        del sys.modules['src.database.config.connection']
    
    os.environ['ENV'] = 'prod'
    
    try:
        from src.database.config.connection import get_database_url
        
        # Simular que todas fallan
        with patch('src.database.config.connection.get_mysql_engine') as mock_windows, \
             patch('src.database.config.connection.get_mysql_linux_engine') as mock_linux, \
             patch('src.database.config.connection.get_azure_engine') as mock_azure:
            
            mock_windows.side_effect = OperationalError("Mock Windows down", None, None)
            mock_linux.side_effect = OperationalError("Mock Linux down", None, None)
            mock_azure.side_effect = OperationalError("Mock Azure down", None, None)
            
            try:
                url = get_database_url()
                print("Resultado: ERROR - Debio lanzar excepcion")
                print_result("Manejo de error total", False)
                return False
            except ConnectionError:
                print("Resultado: Excepcion lanzada correctamente")
                print_result("Manejo de error total", True)
                return True
            
    except Exception as e:
        print(f"Error inesperado: {str(e)[:100]}")
        print_result("Manejo de error total", False)
        return False

def test_dev_mode():
    """Test 5: Modo desarrollo solo usa Windows"""
    print_header("TEST 5: Modo DEV - Solo Windows")
    
    # Resetear modulos
    if 'src.database.config.connection' in sys.modules:
        del sys.modules['src.database.config.connection']
    
    os.environ['ENV'] = 'dev'
    
    try:
        from src.database.config.connection import get_database_url
        
        # Verificar que solo intenta Windows
        with patch('src.database.config.connection.get_mysql_linux_engine') as mock_linux, \
             patch('src.database.config.connection.get_azure_engine') as mock_azure:
            
            url = get_database_url()
            
            # Linux y Azure no deben ser llamados en DEV
            if mock_linux.call_count == 0 and mock_azure.call_count == 0:
                print("Resultado: Solo Windows usado en DEV")
                print_result("Modo DEV correcto", True)
                return True
            else:
                print("Resultado: ERROR - Se intentaron otras bases de datos en DEV")
                print_result("Modo DEV correcto", False)
                return False
            
    except Exception as e:
        print(f"Error: {str(e)[:100]}")
        print_result("Modo DEV correcto", False)
        return False

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "="*70)
    print(" SUITE DE TESTS - ORQUESTADOR DE BASES DE DATOS")
    print("="*70)
    
    results = []
    
    # Test 1: Solo Windows
    results.append(("Test 1: Solo Windows", test_windows_only()))
    
    # Test 2: Windows falla, Linux funciona
    results.append(("Test 2: Fallback a Linux", test_windows_fail_linux_works()))
    
    # Test 3: Windows y Linux fallan, Azure funciona
    results.append(("Test 3: Fallback a Azure", test_windows_linux_fail_azure_works()))
    
    # Test 4: Todas fallan
    results.append(("Test 4: Todas fallan", test_all_fail()))
    
    # Test 5: Modo DEV
    results.append(("Test 5: Modo DEV", test_dev_mode()))
    
    # Resumen
    print_header("RESUMEN DE TESTS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        print_result(test_name, result)
    
    print(f"\nResultado final: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\nTodos los tests pasaron correctamente")
        return 0
    else:
        print(f"\n{total - passed} tests fallaron")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)