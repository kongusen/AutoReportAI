'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AIProviderForm, AIProviderFormValues } from '@/components/AIProviderForm';

interface AIProvider {
  id: number;
  name: string;
  api_base?: string;
  model_name: string;
  // api_key is sensitive and should not be displayed directly
}

export default function AIProvidersPage() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<AIProvider | null>(null);

  const fetchProviders = async () => {
    try {
      setLoading(true);
      const response = await api.get('/ai-providers');
      setProviders(response.data);
    } catch (err) {
      setError('Failed to fetch AI providers.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  const handleFormSubmit = async (values: AIProviderFormValues) => {
    try {
      if (editingProvider) {
        // When updating, we might not have the api_key if it's not being changed.
        // The backend should handle partial updates.
        await api.put(`/ai-providers/${editingProvider.id}`, values);
      } else {
        await api.post('/ai-providers', values);
      }
      setIsModalOpen(false);
      setEditingProvider(null);
      fetchProviders();
    } catch (err) {
      console.error('Failed to save AI provider', err);
    }
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this AI provider?')) {
      try {
        await api.delete(`/ai-providers/${id}`);
        fetchProviders();
      } catch (err) {
        console.error('Failed to delete AI provider', err);
      }
    }
  };

  const openModalForNew = () => {
    setEditingProvider(null);
    setIsModalOpen(true);
  };

  const openModalForEdit = (provider: AIProvider) => {
    setEditingProvider(provider);
    setIsModalOpen(true);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">AI Providers</h1>
        <Button onClick={openModalForNew}>Add New Provider</Button>
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingProvider ? 'Edit AI Provider' : 'Add New AI Provider'}</DialogTitle>
          </DialogHeader>
          <AIProviderForm
            onSubmit={handleFormSubmit}
            // For editing, we pass the full provider object. 
            // The form will not have the api_key unless the user types a new one.
            defaultValues={editingProvider || undefined}
          />
        </DialogContent>
      </Dialog>

      <div className="bg-white shadow-md rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">API Key</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">API Base</th>
              <th className="relative px-6 py-3">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {providers.map((provider) => (
              <tr key={provider.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{provider.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{provider.model_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">**********</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{provider.api_base || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <Button variant="link" onClick={() => openModalForEdit(provider)}>Edit</Button>
                  <Button variant="link" className="text-red-600" onClick={() => handleDelete(provider.id)}>Delete</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
} 