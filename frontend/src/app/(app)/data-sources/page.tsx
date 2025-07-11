'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { DataSourceForm, DataSourceFormValues } from '@/components/DataSourceForm';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface DataSource {
  id: number;
  name: string;
  source_type: 'sql' | 'csv' | 'api';
  db_query?: string;
  file_path?: string;
  api_url?: string;
}

export default function DataSourcesPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);

  const fetchDataSources = async () => {
    try {
      setLoading(true);
      const response = await api.get('/data-sources');
      setDataSources(response.data);
    } catch (err) {
      setError('Failed to fetch data sources.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDataSources();
  }, []);
  
  const handleFormSubmit = async (values: DataSourceFormValues) => {
    try {
      if (editingSource) {
        await api.put(`/data-sources/${editingSource.id}`, values);
      } else {
        await api.post('/data-sources', values);
      }
      setIsModalOpen(false);
      setEditingSource(null);
      fetchDataSources(); // Refresh data
    } catch (err) {
      console.error('Failed to save data source', err);
      // You might want to show an error message to the user here
    }
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this data source?')) {
        try {
            await api.delete(`/data-sources/${id}`);
            fetchDataSources(); // Refresh data
        } catch (err) {
            console.error('Failed to delete data source', err);
        }
    }
  };
  
  const openModalForNew = () => {
    setEditingSource(null);
    setIsModalOpen(true);
  };

  const openModalForEdit = (source: DataSource) => {
    setEditingSource(source);
    setIsModalOpen(true);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Data Sources</h1>
        <Button onClick={openModalForNew}>Add New Source</Button>
      </div>
      
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingSource ? 'Edit Data Source' : 'Add New Data Source'}</DialogTitle>
          </DialogHeader>
          <DataSourceForm 
            onSubmit={handleFormSubmit}
            defaultValues={editingSource || undefined}
          />
        </DialogContent>
      </Dialog>

      <div className="bg-white shadow-md rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
            {/* ... table head ... */}
            <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Details</th>
              <th className="relative px-6 py-3">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {dataSources.map((source) => (
              <tr key={source.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{source.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        source.source_type === 'sql' ? 'bg-blue-100 text-blue-800' :
                        source.source_type === 'csv' ? 'bg-green-100 text-green-800' :
                        'bg-yellow-100 text-yellow-800'
                    }`}>
                        {source.source_type}
                    </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 truncate max-w-xs">
                  {source.db_query || source.file_path || source.api_url}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <Button variant="link" onClick={() => openModalForEdit(source)}>Edit</Button>
                  <Button variant="link" className="text-red-600" onClick={() => handleDelete(source.id)}>Delete</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
} 